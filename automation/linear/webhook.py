"""Verify Linear webhooks, dedupe, and enqueue jobs."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from automation.linear.router import build_job_payload, dedupe_key, route_linear_webhook
from automation.runners.config import load_config, repo_root
from automation.runners.queue import JobQueue


@dataclass(frozen=True)
class WebhookResult:
    status: str
    message: str
    job_id: str | None = None
    queue_depth: int = 0
    active_jobs: int = 0


class DedupeCache:
    def __init__(self, ttl_seconds: float = 120.0) -> None:
        self._ttl = ttl_seconds
        self._seen: dict[str, float] = {}

    def check_and_set(self, key: str) -> bool:
        now = time.time()
        expired = [k for k, ts in self._seen.items() if now - ts > self._ttl]
        for k in expired:
            del self._seen[k]
        if key in self._seen:
            return True
        self._seen[key] = now
        return False


def verify_linear_signature(body: bytes, signature: str | None, secret: str | None) -> bool:
    if not secret:
        return True
    if not signature:
        return False
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    expected = signature.removeprefix("sha256=")
    return hmac.compare_digest(digest, expected)


def _linear_cfg(cfg: dict[str, Any]) -> dict[str, Any]:
    return cfg.get("linear") or {}


def process_linear_webhook(
    payload: dict[str, Any],
    *,
    cfg: dict[str, Any] | None = None,
    dedupe: DedupeCache | None = None,
) -> WebhookResult:
    cfg = cfg or load_config()
    linear = _linear_cfg(cfg)

    project_names = set(linear.get("project_names") or ["NovelGuard"])
    team_names = set(linear.get("team_names") or ["NoverGuard", "NovelGuard"])
    repo_key = str(linear.get("repo_key") or "novelguard")

    route = route_linear_webhook(
        payload,
        project_names=project_names,
        team_names=team_names,
    )
    if route is None:
        return WebhookResult(status="ignored", message="No automation route for this event")

    cache = dedupe or DedupeCache(float(linear.get("dedupe_ttl_seconds") or 120))
    key = dedupe_key(payload, route)
    if cache.check_and_set(key):
        return WebhookResult(status="deduped", message=f"Duplicate suppressed: {key}")

    job_payload = build_job_payload(payload, route, repo_key=repo_key)

    queue_path = Path(cfg.get("queue", {}).get("path", "automation/jobs/queue.sqlite"))
    if not queue_path.is_absolute():
        queue_path = repo_root() / queue_path

    queue = JobQueue(queue_path)
    stats = queue.stats()

    if stats["running"] > 0 or stats["queued"] > 0:
        # Still enqueue — worker is serial; avoids lost events.
        pass

    try:
        queue.enqueue(job_payload)
    except Exception as exc:
        if "UNIQUE constraint failed" in str(exc):
            return WebhookResult(
                status="deduped",
                message=f"Job already queued: {job_payload['id']}",
                job_id=job_payload["id"],
                queue_depth=stats["queued"],
                active_jobs=stats["running"],
            )
        raise

    stats = queue.stats()
    return WebhookResult(
        status="queued",
        message=f"Enqueued {job_payload['id']} → {route.prompt_file}",
        job_id=job_payload["id"],
        queue_depth=stats["queued"],
        active_jobs=stats["running"],
    )


def parse_webhook_body(body: bytes) -> dict[str, Any]:
    data = json.loads(body.decode("utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Webhook body must be a JSON object")
    return data
