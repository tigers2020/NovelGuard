"""Execute move undo from a validated dry-run plan."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from application.move_source_hash import content_hash_for_move
from application.ports.filesystem_apply import ApplyRowResult
from application.recovery_store import JsonlRecoveryStore
from application.undo_dry_run_planner import inspect_move_undo_item
from application.undo_manifest_errors import UndoExecutionError
from application.undo_manifest_loader import parse_and_validate_undo_manifest
from domain.apply_path_policy import (
    DEFAULT_MOVE_DUPLICATE_FOLDER,
    resolve_duplicate_destination_path,
    resolve_under_library_root,
)
from domain.recovery_models import (
    UndoDryRunPlan,
    UndoExecutionItemResult,
    UndoExecutionResult,
    UndoManifestItem,
    UndoManifestStatus,
)
from infrastructure.local_filesystem_apply import LocalFilesystemApplyAdapter

EXECUTION_ELIGIBLE_STATUSES = frozenset({"pending", "partial", "executing"})


def _default_now() -> datetime:
    return datetime.now(UTC)


def _iso_z(dt: datetime) -> str:
    return dt.isoformat().replace("+00:00", "Z")


def execute_move_undo_from_store(
    *,
    library_root: Path,
    store: JsonlRecoveryStore,
    plan: UndoDryRunPlan,
    filesystem: LocalFilesystemApplyAdapter | None = None,
    now_fn: Callable[[], datetime] | None = None,
) -> UndoExecutionResult:
    if plan.undo_plan_id is None or not plan.undo_plan_id.strip():
        raise UndoExecutionError("PLAN_REQUIRED", "validated dry-run plan is required")

    raw = store.read_undo_manifest_raw(plan.undo_plan_id)
    return execute_move_undo(
        library_root=library_root,
        store=store,
        plan=plan,
        manifest_raw=raw,
        filesystem=filesystem,
        now_fn=now_fn,
    )


def execute_move_undo(
    *,
    library_root: Path,
    store: JsonlRecoveryStore,
    plan: UndoDryRunPlan,
    manifest_raw: dict,
    filesystem: LocalFilesystemApplyAdapter | None = None,
    now_fn: Callable[[], datetime] | None = None,
) -> UndoExecutionResult:
    if plan.undo_plan_id is None or not plan.undo_plan_id.strip():
        raise UndoExecutionError("PLAN_REQUIRED", "validated dry-run plan is required")

    undo_plan_id = manifest_raw.get("undoPlanId")
    if undo_plan_id != plan.undo_plan_id:
        raise UndoExecutionError(
            "PLAN_MANIFEST_MISMATCH",
            f"plan undoPlanId {plan.undo_plan_id!r} does not match manifest {undo_plan_id!r}",
        )

    manifest_status = manifest_raw.get("status")
    if manifest_status == "completed":
        return _completed_no_op(plan)

    if manifest_status not in EXECUTION_ELIGIBLE_STATUSES:
        raise UndoExecutionError(
            "MANIFEST_NOT_ELIGIBLE",
            f"manifest status not eligible for execution: {manifest_status!r}",
        )

    manifest = parse_and_validate_undo_manifest(manifest_raw)
    if manifest.library_id != plan.library_id or manifest.run_id != plan.run_id:
        raise UndoExecutionError("PLAN_MANIFEST_MISMATCH", "plan metadata does not match manifest")

    fs = filesystem or LocalFilesystemApplyAdapter()
    now = now_fn or _default_now
    manifest_by_id = {item.operation_id: item for item in manifest.items}

    executing_raw = dict(manifest_raw)
    executing_raw["status"] = "executing"
    store.update_undo_manifest(executing_raw)

    excluded_results = _excluded_results(plan)
    candidate_ids = {item.operation_id for item in plan.items if item.status == "recoverable"}
    ordered_candidates = sorted(
        (item for item in plan.items if item.operation_id in candidate_ids),
        key=lambda item: item.sequence,
        reverse=True,
    )

    execution_items: list[UndoExecutionItemResult] = list(excluded_results)
    for plan_item in ordered_candidates:
        manifest_item = manifest_by_id[plan_item.operation_id]
        if _is_already_recovered(library_root=library_root, item=manifest_item):
            execution_items.append(
                UndoExecutionItemResult(
                    operation_id=plan_item.operation_id,
                    sequence=plan_item.sequence,
                    status="already_recovered",
                    reason=None,
                )
            )
            continue

        recheck = inspect_move_undo_item(library_root=library_root, item=manifest_item)
        if recheck.status != "recoverable":
            execution_items.append(
                UndoExecutionItemResult(
                    operation_id=plan_item.operation_id,
                    sequence=plan_item.sequence,
                    status="recovery_failed",
                    reason=recheck.reason,
                )
            )
            continue

        move_result = _move_back(library_root=library_root, item=manifest_item, filesystem=fs)
        if move_result.outcome != "ok":
            execution_items.append(
                UndoExecutionItemResult(
                    operation_id=plan_item.operation_id,
                    sequence=plan_item.sequence,
                    status="recovery_failed",
                    reason="move_error",
                )
            )
            continue

        execution_items.append(
            UndoExecutionItemResult(
                operation_id=plan_item.operation_id,
                sequence=plan_item.sequence,
                status="recovered",
                reason=None,
            )
        )

    recovered_count = sum(1 for item in execution_items if item.status == "recovered")
    already_recovered_count = sum(
        1 for item in execution_items if item.status == "already_recovered"
    )
    failed_count = sum(1 for item in execution_items if item.status == "recovery_failed")
    excluded_count = sum(1 for item in execution_items if item.status == "excluded")

    final_status = _final_manifest_status(
        candidate_count=len(ordered_candidates),
        recovered_count=recovered_count,
        already_recovered_count=already_recovered_count,
        failed_count=failed_count,
    )
    execution_payload = {
        "executedAt": _iso_z(now()),
        "recoveredCount": recovered_count,
        "alreadyRecoveredCount": already_recovered_count,
        "failedCount": failed_count,
        "excludedCount": excluded_count,
        "items": [item.to_dict() for item in execution_items],
    }
    finalized_raw = dict(manifest_raw)
    finalized_raw["status"] = final_status
    finalized_raw["execution"] = execution_payload
    store.update_undo_manifest(finalized_raw)

    return UndoExecutionResult(
        undo_plan_id=plan.undo_plan_id,
        manifest_status=final_status,
        no_op=False,
        recovered_count=recovered_count,
        already_recovered_count=already_recovered_count,
        failed_count=failed_count,
        excluded_count=excluded_count,
        items=tuple(execution_items),
    )


def _completed_no_op(plan: UndoDryRunPlan) -> UndoExecutionResult:
    return UndoExecutionResult(
        undo_plan_id=plan.undo_plan_id,
        manifest_status="completed",
        no_op=True,
        recovered_count=0,
        already_recovered_count=0,
        failed_count=0,
        excluded_count=0,
        items=(),
    )


def _excluded_results(plan: UndoDryRunPlan) -> list[UndoExecutionItemResult]:
    excluded: list[UndoExecutionItemResult] = []
    for item in plan.items:
        if item.status == "recoverable":
            continue
        excluded.append(
            UndoExecutionItemResult(
                operation_id=item.operation_id,
                sequence=item.sequence,
                status="excluded",
                reason=item.reason,
            )
        )
    return excluded


def _final_manifest_status(
    *,
    candidate_count: int,
    recovered_count: int,
    already_recovered_count: int,
    failed_count: int,
) -> UndoManifestStatus:
    if candidate_count == 0:
        return "completed"
    if failed_count > 0:
        return "partial"
    if recovered_count + already_recovered_count >= candidate_count:
        return "completed"
    return "partial"


def _is_already_recovered(*, library_root: Path, item: UndoManifestItem) -> bool:
    current_path, current_reason = resolve_duplicate_destination_path(
        library_root,
        DEFAULT_MOVE_DUPLICATE_FOLDER,
        item.from_path,
    )
    source_path, source_reason = resolve_under_library_root(library_root, item.to_path)
    if (
        current_reason is not None
        or source_reason is not None
        or current_path is None
        or source_path is None
    ):
        return False
    if current_path.is_file():
        return False
    if not source_path.is_file():
        return False

    before_hash = item.checkpoint_ref.get("beforeHash")
    if not before_hash:
        return True

    stat = source_path.stat()
    actual_hash = content_hash_for_move(source_path, size_bytes=stat.st_size)
    return actual_hash == before_hash


def _move_back(
    *,
    library_root: Path,
    item: UndoManifestItem,
    filesystem: LocalFilesystemApplyAdapter,
):
    current_path, current_reason = resolve_duplicate_destination_path(
        library_root,
        DEFAULT_MOVE_DUPLICATE_FOLDER,
        item.from_path,
    )
    source_path, source_reason = resolve_under_library_root(library_root, item.to_path)
    if (
        current_reason is not None
        or source_reason is not None
        or current_path is None
        or source_path is None
    ):
        return ApplyRowResult(outcome="error", error="malformed_item")
    return filesystem.move_file(current_path, source_path)
