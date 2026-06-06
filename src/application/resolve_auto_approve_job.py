"""Resolve bulk auto-approve background job (spec 035 slice 2 — dry-run polling only)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Callable

_JOB_STATUSES = frozenset({"idle", "running", "complete", "error", "cancelled"})
_JOB_PHASES = frozenset({"idle", "set_keeper", "approve", "persist", "summarize"})


class ResolveAutoApproveJobCancelled(Exception):
    """Cooperative cancel requested during dry-run scan."""


def _iso_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def idle_resolve_auto_approve_job_snapshot() -> dict[str, Any]:
    return build_resolve_auto_approve_job_snapshot()


def build_resolve_auto_approve_job_snapshot(
    *,
    status: str = "idle",
    phase: str = "idle",
    processed_rows: int = 0,
    total_rows: int = 0,
    keeper_count: int = 0,
    move_candidate_count: int = 0,
    scanned_count: int = 0,
    eligible_count: int = 0,
    skipped_conflict_count: int = 0,
    skipped_excluded_count: int = 0,
    label: str = "",
    error: str | None = None,
    started_at: str | None = None,
    finished_at: str | None = None,
    summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "status": status,
        "phase": phase,
        "processedRows": processed_rows,
        "totalRows": total_rows,
        "keeperCount": keeper_count,
        "moveCandidateCount": move_candidate_count,
        "scannedCount": scanned_count,
        "eligibleCount": eligible_count,
        "skippedConflictCount": skipped_conflict_count,
        "skippedExcludedCount": skipped_excluded_count,
        "label": label,
        "error": error,
        "startedAt": started_at,
        "finishedAt": finished_at,
        "summary": summary,
    }


def validate_resolve_auto_approve_job_snapshot(payload: Any) -> None:
    if not isinstance(payload, dict):
        raise ValueError("resolveAutoApproveJob must be a dict")
    status = payload.get("status")
    if status not in _JOB_STATUSES:
        raise ValueError(f"invalid resolveAutoApproveJob.status: {status!r}")
    phase = payload.get("phase")
    if phase not in _JOB_PHASES:
        raise ValueError(f"invalid resolveAutoApproveJob.phase: {phase!r}")
    for key in (
        "processedRows",
        "totalRows",
        "keeperCount",
        "moveCandidateCount",
        "scannedCount",
        "eligibleCount",
        "skippedConflictCount",
        "skippedExcludedCount",
    ):
        value = payload.get(key)
        if not isinstance(value, int) or value < 0:
            raise ValueError(f"resolveAutoApproveJob.{key} must be a non-negative int")
    if not isinstance(payload.get("label"), str):
        raise ValueError("resolveAutoApproveJob.label must be a string")
    error = payload.get("error")
    if error is not None and not isinstance(error, str):
        raise ValueError("resolveAutoApproveJob.error must be a string or null")
    for key in ("startedAt", "finishedAt"):
        value = payload.get(key)
        if value is not None and not isinstance(value, str):
            raise ValueError(f"resolveAutoApproveJob.{key} must be a string or null")
    summary = payload.get("summary")
    if summary is not None and not isinstance(summary, dict):
        raise ValueError("resolveAutoApproveJob.summary must be a dict or null")


ProgressCallback = Callable[[dict[str, int]], None]
CancelCheck = Callable[[], bool]


def run_resolve_auto_approve_dry_run(
    all_rows: list[dict[str, Any]],
    query: dict[str, Any],
    *,
    files_by_id: dict[str, Any],
    members_by_group: dict[str, set[str]],
    on_progress: ProgressCallback | None = None,
    cancel_check: CancelCheck | None = None,
) -> dict[str, Any]:
    """Compute dry-run summary asynchronously; no review mutations."""
    from application.summarize_resolve_auto_approve import summarize_resolve_auto_approve

    def _progress(scanned: int) -> None:
        if on_progress is None:
            return
        on_progress(
            {
                "scannedCount": scanned,
                "processedRows": scanned,
            }
        )
        if cancel_check and cancel_check():
            raise ResolveAutoApproveJobCancelled()

    summary = summarize_resolve_auto_approve(
        all_rows,
        query,
        files_by_id=files_by_id,
        members_by_group=members_by_group,
        on_page_scanned=_progress,
        cancel_check=cancel_check,
    )
    eligible = int(summary["unreviewedCount"])
    if on_progress is not None:
        on_progress(
            {
                "scannedCount": eligible,
                "processedRows": eligible,
                "totalRows": eligible,
                "eligibleCount": eligible,
                "keeperCount": int(summary["keeperCount"]),
                "moveCandidateCount": int(summary["moveCandidateCount"]),
                "skippedConflictCount": int(summary["skippedConflictCount"]),
                "skippedExcludedCount": int(summary["skippedExcludedCount"]),
            }
        )
    return summary
