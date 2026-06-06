"""Finalize verification background job."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

_JOB_STATUSES = frozenset({"idle", "queued", "running", "succeeded", "failed", "cancelled"})


def _iso_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def new_finalize_job_id() -> str:
    return f"finalize-{uuid4().hex}"


def idle_finalize_job_snapshot() -> dict[str, Any]:
    return build_finalize_job_snapshot()


def build_finalize_job_snapshot(
    *,
    job_id: str | None = None,
    status: str = "idle",
    progress: int = 0,
    message: str = "",
    started_at: str | None = None,
    finished_at: str | None = None,
    result: dict[str, Any] | None = None,
    error: str | None = None,
) -> dict[str, Any]:
    return {
        "jobId": job_id,
        "status": status,
        "progress": progress,
        "message": message,
        "startedAt": started_at,
        "finishedAt": finished_at,
        "result": result,
        "error": error,
    }


def validate_finalize_job_snapshot(payload: Any) -> None:
    if not isinstance(payload, dict):
        raise ValueError("finalizeJob must be a dict")
    status = payload.get("status")
    if status not in _JOB_STATUSES:
        raise ValueError(f"invalid finalizeJob.status: {status!r}")
    progress = payload.get("progress")
    if not isinstance(progress, int) or progress < 0 or progress > 100:
        raise ValueError("finalizeJob.progress must be an int between 0 and 100")
    if not isinstance(payload.get("message"), str):
        raise ValueError("finalizeJob.message must be a string")
    job_id = payload.get("jobId")
    if job_id is not None and not isinstance(job_id, str):
        raise ValueError("finalizeJob.jobId must be a string or null")
    error = payload.get("error")
    if error is not None and not isinstance(error, str):
        raise ValueError("finalizeJob.error must be a string or null")
    for key in ("startedAt", "finishedAt"):
        value = payload.get(key)
        if value is not None and not isinstance(value, str):
            raise ValueError(f"finalizeJob.{key} must be a string or null")
    result = payload.get("result")
    if result is not None and not isinstance(result, dict):
        raise ValueError("finalizeJob.result must be a dict or null")
