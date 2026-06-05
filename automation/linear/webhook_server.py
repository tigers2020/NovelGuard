"""HTTP server for Linear webhooks → automation queue."""

from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from automation.linear.webhook import (
    DedupeCache,
    parse_webhook_body,
    process_linear_webhook,
    verify_linear_signature,
)
from automation.runners.config import load_config
from automation.runners.emit import emit_or_print
from automation.runners.runtime_state import get_runtime_state


def _runtime_state_or_none():
    try:
        return get_runtime_state()
    except RuntimeError:
        return None


class LinearWebhookHandler(BaseHTTPRequestHandler):
    dedupe_cache = DedupeCache()
    cfg: dict[str, Any] = {}

    def log_message(self, format: str, *args: Any) -> None:
        summary = f"{args[0]}" if args else format
        emit_or_print("webhook", "webhook.log", summary, plain_prefix=f"[webhook] {summary}")

    def _respond(self, status: int, body: dict[str, Any]) -> None:
        payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self) -> None:
        if self.path.rstrip("/") in ("", "/health", "/healthz"):
            self._respond(200, {"ok": True, "service": "novelguard-linear-webhook"})
            return
        self._respond(404, {"ok": False, "error": "not found"})

    def do_POST(self) -> None:
        linear_cfg = self.cfg.get("linear") or {}
        path = self.path.rstrip("/") or "/"
        expected_path = str(linear_cfg.get("webhook_path") or "/linear/webhook")
        if path != expected_path:
            self._respond(404, {"ok": False, "error": "not found"})
            return

        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length)
        secret = os.environ.get("LINEAR_WEBHOOK_SECRET") or linear_cfg.get("webhook_secret")
        signature = self.headers.get("Linear-Signature") or self.headers.get("linear-signature")

        if not verify_linear_signature(body, signature, secret):
            self._respond(401, {"ok": False, "error": "invalid signature"})
            return

        try:
            payload = parse_webhook_body(body)
            result = process_linear_webhook(
                payload,
                cfg=self.cfg,
                dedupe=self.dedupe_cache,
            )
            issue = (payload.get("data") or {}).get("identifier") or "?"
            summary = (
                f"POST {path} issue={issue} "
                f"status={result.status} job_id={result.job_id or '-'} "
                f"msg={result.message}"
            )
            emit_or_print("webhook", "webhook.post", summary, plain_prefix=f"[webhook] {summary}")

            state = _runtime_state_or_none()
            if state is not None:
                state.queued = result.queue_depth
                state.running = result.active_jobs

            self._respond(
                200,
                {
                    "ok": True,
                    "status": result.status,
                    "message": result.message,
                    "job_id": result.job_id,
                    "job_ids": list(result.job_ids),
                    "queue_depth": result.queue_depth,
                    "active_jobs": result.active_jobs,
                },
            )
        except json.JSONDecodeError:
            self._respond(400, {"ok": False, "error": "invalid json"})
        except Exception as exc:
            self._respond(500, {"ok": False, "error": str(exc)})


def serve(host: str = "127.0.0.1", port: int = 8765, cfg: dict[str, Any] | None = None) -> None:
    cfg = cfg or load_config()
    linear = cfg.get("linear") or {}
    host = str(linear.get("webhook_host") or host)
    port = int(linear.get("webhook_port") or port)

    LinearWebhookHandler.cfg = cfg
    server = ThreadingHTTPServer((host, port), LinearWebhookHandler)
    webhook_path = linear.get("webhook_path", "/linear/webhook")
    emit_or_print(
        "webhook",
        "webhook.listen",
        f"http://{host}:{port}{webhook_path}",
        plain_prefix=(
            f"Linear webhook listening on http://{host}:{port}{webhook_path}\n"
            "Health: GET /health"
        ),
    )
    server.serve_forever()
