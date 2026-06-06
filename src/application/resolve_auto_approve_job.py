"""Resolve bulk auto-approve background job (spec 035)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Callable, Protocol

JOB_MUTATION_CHUNK = 200

_JOB_STATUSES = frozenset({"idle", "running", "complete", "error", "cancelled"})
_JOB_PHASES = frozenset({"idle", "set_keeper", "approve", "persist", "summarize"})

_PHASE_LABELS = {
    "summarize": "미검토 대상 집계 중…",
    "set_keeper": "키퍼 선정 반영 중…",
    "approve": "승인 반영 중…",
    "persist": "검토 인덱스 동기화 중…",
}


class ResolveAutoApproveJobCancelled(Exception):
    """Cooperative cancel requested during job execution."""


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
    keeper_set_count: int = 0,
    approved_row_count: int = 0,
    mutation_count: int = 0,
    persisted_revision: int | None = None,
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
        "keeperSetCount": keeper_set_count,
        "approvedRowCount": approved_row_count,
        "mutationCount": mutation_count,
        "persistedRevision": persisted_revision,
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
        "keeperSetCount",
        "approvedRowCount",
        "mutationCount",
    ):
        value = payload.get(key)
        if not isinstance(value, int) or value < 0:
            raise ValueError(f"resolveAutoApproveJob.{key} must be a non-negative int")
    persisted_revision = payload.get("persistedRevision")
    if persisted_revision is not None and (
        not isinstance(persisted_revision, int) or persisted_revision < 0
    ):
        raise ValueError(
            "resolveAutoApproveJob.persistedRevision must be a non-negative int or null"
        )
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


ProgressCallback = Callable[[dict[str, Any]], None]
CancelCheck = Callable[[], bool]


class ResolveAutoApproveJobMutator(Protocol):
    def apply_review_decisions(
        self,
        selection: dict[str, Any],
        command: str,
        *,
        keeper_file_id: str | None = None,
    ) -> int: ...

    def finalize_projection(self) -> None: ...

    def library_revision(self) -> int: ...


def _chunk_row_ids(row_ids: list[str], chunk_size: int = JOB_MUTATION_CHUNK) -> list[list[str]]:
    if not row_ids:
        return []
    return [row_ids[index : index + chunk_size] for index in range(0, len(row_ids), chunk_size)]


def _explicit_selection(row_ids: list[str]) -> dict[str, Any]:
    return {"type": "explicit_rows", "rowIds": row_ids}


def _raise_if_cancelled(cancel_check: CancelCheck | None) -> None:
    if cancel_check is not None and cancel_check():
        raise ResolveAutoApproveJobCancelled()


@dataclass(frozen=True)
class ResolveAutoApproveJobResult:
    summary: dict[str, Any]
    keeper_set_count: int
    approved_row_count: int
    mutation_count: int
    persisted_revision: int | None


def run_resolve_auto_approve_dry_run(
    all_rows: list[dict[str, Any]],
    query: dict[str, Any],
    *,
    files_by_id: dict[str, Any],
    members_by_group: dict[str, set[str]],
    on_progress: ProgressCallback | None = None,
    cancel_check: CancelCheck | None = None,
) -> dict[str, Any]:
    """Compute dry-run summary; no review mutations."""
    from application.summarize_resolve_auto_approve import summarize_resolve_auto_approve

    def _progress(scanned: int) -> None:
        if on_progress is None:
            return
        on_progress(
            {
                "phase": "summarize",
                "scannedCount": scanned,
                "processedRows": scanned,
                "label": _PHASE_LABELS["summarize"],
            }
        )
        _raise_if_cancelled(cancel_check)

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
                "phase": "summarize",
                "scannedCount": eligible,
                "processedRows": eligible,
                "totalRows": eligible,
                "eligibleCount": eligible,
                "keeperCount": int(summary["keeperCount"]),
                "moveCandidateCount": int(summary["moveCandidateCount"]),
                "skippedConflictCount": int(summary["skippedConflictCount"]),
                "skippedExcludedCount": int(summary["skippedExcludedCount"]),
                "label": _PHASE_LABELS["summarize"],
            }
        )
    return summary


def run_resolve_auto_approve_job(
    all_rows: list[dict[str, Any]],
    query: dict[str, Any],
    *,
    files_by_id: dict[str, Any],
    members_by_group: dict[str, set[str]],
    mutator: ResolveAutoApproveJobMutator,
    on_progress: ProgressCallback | None = None,
    cancel_check: CancelCheck | None = None,
) -> ResolveAutoApproveJobResult:
    """Summarize then apply keeper/approve mutations in internal chunks."""
    revision_before = mutator.library_revision()

    summary = run_resolve_auto_approve_dry_run(
        all_rows,
        query,
        files_by_id=files_by_id,
        members_by_group=members_by_group,
        on_progress=on_progress,
        cancel_check=cancel_check,
    )
    _raise_if_cancelled(cancel_check)

    keeper_row_ids = [str(row_id) for row_id in summary.get("keeperRowIds", [])]
    approve_row_ids = [str(row_id) for row_id in summary.get("approveRowIds", [])]
    total_rows = len(approve_row_ids)
    keeper_set_count = 0
    approved_row_count = 0

    for chunk_index, chunk in enumerate(_chunk_row_ids(keeper_row_ids)):
        _raise_if_cancelled(cancel_check)
        updated = mutator.apply_review_decisions(_explicit_selection(chunk), "setKeeper")
        keeper_set_count += updated
        processed = min((chunk_index + 1) * JOB_MUTATION_CHUNK, len(keeper_row_ids))
        if on_progress is not None:
            on_progress(
                {
                    "phase": "set_keeper",
                    "processedRows": processed,
                    "totalRows": total_rows,
                    "keeperSetCount": keeper_set_count,
                    "approvedRowCount": approved_row_count,
                    "mutationCount": keeper_set_count + approved_row_count,
                    "label": _PHASE_LABELS["set_keeper"],
                }
            )

    for chunk_index, chunk in enumerate(_chunk_row_ids(approve_row_ids)):
        _raise_if_cancelled(cancel_check)
        updated = mutator.apply_review_decisions(_explicit_selection(chunk), "approve")
        approved_row_count += updated
        processed = min((chunk_index + 1) * JOB_MUTATION_CHUNK, len(approve_row_ids))
        if on_progress is not None:
            on_progress(
                {
                    "phase": "approve",
                    "processedRows": processed,
                    "totalRows": total_rows,
                    "keeperSetCount": keeper_set_count,
                    "approvedRowCount": approved_row_count,
                    "mutationCount": keeper_set_count + approved_row_count,
                    "label": _PHASE_LABELS["approve"],
                }
            )

    _raise_if_cancelled(cancel_check)
    mutator.finalize_projection()
    mutation_count = keeper_set_count + approved_row_count
    persisted_revision = mutator.library_revision() if mutation_count > 0 else revision_before

    if on_progress is not None:
        on_progress(
            {
                "phase": "persist",
                "processedRows": total_rows,
                "totalRows": total_rows,
                "keeperSetCount": keeper_set_count,
                "approvedRowCount": approved_row_count,
                "mutationCount": keeper_set_count + approved_row_count,
                "persistedRevision": persisted_revision,
                "label": _PHASE_LABELS["persist"],
            }
        )

    return ResolveAutoApproveJobResult(
        summary=summary,
        keeper_set_count=keeper_set_count,
        approved_row_count=approved_row_count,
        mutation_count=mutation_count,
        persisted_revision=persisted_revision,
    )
