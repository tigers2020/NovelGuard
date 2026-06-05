"""Verify Linear webhooks, dedupe, and enqueue jobs."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from automation.linear.router import build_job_payload, dedupe_key, route_linear_webhook_events
from automation.runners.config import load_config, repo_root
from automation.runners.queue import JobQueue


@dataclass(frozen=True)
class WebhookResult:
    status: str
    message: str
    job_id: str | None = None
    job_ids: tuple[str, ...] = ()
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

    event_routes = route_linear_webhook_events(
        payload,
        project_names=project_names,
        team_names=team_names,
    )
    if not event_routes:
        return WebhookResult(status="ignored", message="No automation route for this event")

    cache = dedupe or DedupeCache(float(linear.get("dedupe_ttl_seconds") or 120))
    queue_path = Path(cfg.get("queue", {}).get("path", "automation/jobs/queue.sqlite"))
    if not queue_path.is_absolute():
        queue_path = repo_root() / queue_path

    queue = JobQueue(queue_path)
    queued_ids: list[str] = []
    deduped_ids: list[str] = []

    for event_route in event_routes:
        route = event_route.route
        key = dedupe_key(payload, route)
        if cache.check_and_set(key):
            deduped_ids.append(key)
            continue

        job_payload = build_job_payload(payload, route, repo_key=repo_key)
        job_payload["meta"]["linear_event"] = event_route.event

        try:
            queue.enqueue(job_payload)
            queued_ids.append(job_payload["id"])
        except Exception as exc:
            if (
                "already active" in str(exc)
                or "already succeeded" in str(exc)
                or "UNIQUE constraint failed" in str(exc)
            ):
                deduped_ids.append(job_payload["id"])
                continue
            raise

    stats = queue.stats()
    if queued_ids:
        status = "queued"
        message = f"Enqueued {len(queued_ids)} job(s): {', '.join(queued_ids)}"
    elif deduped_ids:
        status = "deduped"
        message = f"Duplicate suppressed: {', '.join(deduped_ids)}"
    else:
        status = "ignored"
        message = "No new automation job for this event"

    return WebhookResult(
        status=status,
        message=message,
        job_id=queued_ids[0] if queued_ids else None,
        job_ids=tuple(queued_ids),
        queue_depth=stats["queued"],
        active_jobs=stats["running"],
    )


def parse_webhook_body(body: bytes) -> dict[str, Any]:
    data = json.loads(body.decode("utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Webhook body must be a JSON object")
    return data
