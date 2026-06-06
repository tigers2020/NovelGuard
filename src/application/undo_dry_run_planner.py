"""Read-only dry-run planner for move undo manifests."""

from __future__ import annotations

from pathlib import Path

from application.move_source_hash import content_hash_for_move
from application.recovery_store import JsonlRecoveryStore
from application.undo_manifest_loader import parse_and_validate_undo_manifest
from domain.apply_path_policy import (
    DEFAULT_MOVE_DUPLICATE_FOLDER,
    resolve_duplicate_destination_path,
    resolve_under_library_root,
)
from domain.recovery_models import (
    DryRunItemReason,
    DryRunItemStatus,
    UndoDryRunItemResult,
    UndoDryRunPlan,
    UndoManifest,
    UndoManifestItem,
)


def plan_move_undo_from_store(
    *,
    library_root: Path,
    store: JsonlRecoveryStore,
    undo_plan_id: str,
) -> UndoDryRunPlan:
    raw = store.read_undo_manifest_raw(undo_plan_id)
    manifest = parse_and_validate_undo_manifest(raw)
    return plan_move_undo_dry_run(
        library_root=library_root,
        manifest=manifest,
        manifest_path=str(store.undo_manifest_path(undo_plan_id)),
    )


def plan_move_undo_dry_run(
    *,
    library_root: Path,
    manifest: UndoManifest,
    manifest_path: str | None = None,
) -> UndoDryRunPlan:
    items = tuple(
        _inspect_move_back_item(library_root=library_root, item=item) for item in manifest.items
    )
    recoverable_count = sum(1 for item in items if item.status == "recoverable")
    blocked_count = sum(1 for item in items if item.status == "blocked")
    manual_required_count = sum(1 for item in items if item.status == "manual_required")
    return UndoDryRunPlan(
        undo_plan_id=manifest.undo_plan_id,
        manifest_path=manifest_path,
        library_id=manifest.library_id,
        run_id=manifest.run_id,
        total_count=len(items),
        recoverable_count=recoverable_count,
        blocked_count=blocked_count,
        manual_required_count=manual_required_count,
        items=items,
    )


def _inspect_move_back_item(
    *,
    library_root: Path,
    item: UndoManifestItem,
) -> UndoDryRunItemResult:
    base = _base_result(item)
    if item.undo_action != "move_back" or item.operation_type != "move_duplicate":
        return _with_status(base, "blocked", "unsupported_operation")

    if not item.from_path.strip() or not item.to_path.strip():
        return _with_status(base, "blocked", "malformed_item")

    current_path, current_reason = resolve_duplicate_destination_path(
        library_root,
        DEFAULT_MOVE_DUPLICATE_FOLDER,
        item.from_path,
    )
    if current_reason is not None or current_path is None:
        return _with_status(base, "blocked", "malformed_item")

    source_path, source_reason = resolve_under_library_root(library_root, item.to_path)
    if source_reason is not None or source_path is None:
        return _with_status(base, "blocked", "malformed_item")

    if not current_path.is_file():
        return _with_status(base, "blocked", "dest_missing")

    expected_hash = item.checkpoint_ref.get("afterHash")
    if expected_hash:
        stat = current_path.stat()
        current_hash = content_hash_for_move(current_path, size_bytes=stat.st_size)
        if current_hash != expected_hash:
            return _classify_drift(base, item, "dest_changed")

    if source_path.exists():
        return _classify_collision(base, item)

    return _with_status(base, "recoverable", None)


def _classify_drift(
    base: UndoDryRunItemResult,
    item: UndoManifestItem,
    reason: DryRunItemReason,
) -> UndoDryRunItemResult:
    if item.drift_policy == "manual":
        return _with_status(base, "manual_required", reason)
    return _with_status(base, "blocked", reason)


def _classify_collision(
    base: UndoDryRunItemResult,
    item: UndoManifestItem,
) -> UndoDryRunItemResult:
    if item.collision_policy == "manual":
        return _with_status(base, "manual_required", "source_occupied")
    return _with_status(base, "blocked", "source_occupied")


def _base_result(item: UndoManifestItem) -> UndoDryRunItemResult:
    return UndoDryRunItemResult(
        operation_id=item.operation_id,
        sequence=item.sequence,
        from_path=item.from_path,
        to_path=item.to_path,
        status="blocked",
        reason=None,
    )


def _with_status(
    base: UndoDryRunItemResult,
    status: DryRunItemStatus,
    reason: DryRunItemReason | None,
) -> UndoDryRunItemResult:
    return UndoDryRunItemResult(
        operation_id=base.operation_id,
        sequence=base.sequence,
        from_path=base.from_path,
        to_path=base.to_path,
        status=status,
        reason=reason,
    )
