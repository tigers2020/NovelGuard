#!/usr/bin/env python3
"""Check Linear webhook chain: ngrok → serve → queue.

Usage:
  python scripts/linear_webhook_doctor.py
  python scripts/linear_webhook_doctor.py --smoke-post
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path


def _get_json(url: str, *, timeout: float = 3.0) -> dict | None:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return None


def main(argv: list[str] | None = None) -> int:
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root))

    from automation.runners.config import load_config

    parser = argparse.ArgumentParser(description="Diagnose Linear → ngrok → webhook → queue")
    parser.add_argument(
        "--smoke-post",
        action="store_true",
        help="POST a minimal Issue update payload to the public ngrok URL",
    )
    args = parser.parse_args(argv)

    cfg = load_config()
    linear = cfg.get("linear") or {}
    host = str(linear.get("webhook_host") or "127.0.0.1")
    port = int(linear.get("webhook_port") or 8765)
    path = str(linear.get("webhook_path") or "/linear/webhook")
    configured_public = str(linear.get("webhook_public_url") or "").rstrip("/")
    secret = linear.get("webhook_secret") or ""

    checks: list[dict[str, str]] = []

    health = _get_json(f"http://{host}:{port}/health")
    if health and health.get("ok"):
        checks.append({"check": "webhook serve", "status": "ok", "detail": f"http://{host}:{port}/health"})
    else:
        checks.append(
            {
                "check": "webhook serve",
                "status": "FAIL",
                "detail": f"Not listening on {host}:{port}. Run: python scripts/linear_webhook_handler.py serve",
            }
        )

    ngrok_public: str | None = None
    tunnels = _get_json("http://127.0.0.1:4040/api/tunnels")
    if tunnels and isinstance(tunnels.get("tunnels"), list):
        for t in tunnels["tunnels"]:
            addr = str((t.get("config") or {}).get("addr") or "")
            pub = str(t.get("public_url") or "")
            if f":{port}" in addr or addr.endswith(str(port)):
                ngrok_public = pub.rstrip("/")
                break
        if ngrok_public:
            checks.append({"check": "ngrok tunnel", "status": "ok", "detail": ngrok_public})
        else:
            checks.append(
                {
                    "check": "ngrok tunnel",
                    "status": "FAIL",
                    "detail": f"No tunnel to port {port}. Run: ngrok http {port}",
                }
            )
    else:
        checks.append(
            {
                "check": "ngrok tunnel",
                "status": "FAIL",
                "detail": "ngrok not running (http://127.0.0.1:4040 unreachable)",
            }
        )

    linear_url = (
        f"{configured_public}{path}"
        if configured_public
        else (f"{ngrok_public}{path}" if ngrok_public else f"https://<ngrok-host>{path}")
    )

    print(json.dumps({"checks": checks}, indent=2, ensure_ascii=False))
    print()
    print("=== Linear webhook (one-time setup) ===")
    print("Linear -> Settings -> Administration -> API -> Webhooks -> Create webhook")
    print(f"  URL:      {linear_url}")
    print("  Events:   Issues (Issue create + update)")
    print("  Team:     NoverGuard (NovelGuard project)")
    if secret:
        print("  Secret:   matches automation/config.yaml linear.webhook_secret")
    else:
        print("  Secret:   optional (leave empty in Linear + config, or set both)")
    print()
    print("If http://127.0.0.1:4040/inspect/http shows NO POST from Linear:")
    print("  -> webhook URL not registered in Linear, or wrong team/ngrok URL.")
    print("  -> Cursor MCP status changes do NOT bypass this - Linear cloud must POST.")
    print()
    print("After setup: change issue status in Linear UI → inspect should show POST →")
    print("  serve terminal: [webhook] enqueue status=queued ...")
    print("  worker terminal: claimed job ...")

    if args.smoke_post and ngrok_public:
        fixture = root / "automation/examples/linear-webhook-issue-update-nov15-todo-plan.json"
        body = fixture.read_bytes()
        req = urllib.request.Request(
            linear_url,
            data=body,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                result = json.loads(resp.read().decode("utf-8"))
            print()
            print("=== smoke POST (via ngrok) ===")
            print(json.dumps(result, indent=2, ensure_ascii=False))
        except urllib.error.HTTPError as exc:
            print()
            print(f"smoke POST failed: HTTP {exc.code} {exc.read().decode('utf-8', errors='replace')}")
            return 1

    failed = [c for c in checks if c["status"] == "FAIL"]
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
