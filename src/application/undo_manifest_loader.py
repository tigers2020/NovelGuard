"""Parse and validate sealed move-apply undo manifests."""

from __future__ import annotations

from typing import Any

from application.undo_manifest_errors import UndoManifestValidationError
from domain.recovery_models import UndoManifest, UndoManifestItem

SUPPORTED_SCHEMA_VERSION = 1
MOVE_APPLY_BATCH_KIND = "move_apply"
MOVE_UNDO_OPERATION_TYPE = "move_duplicate"
MOVE_UNDO_ACTION = "move_back"
DRY_RUN_ALLOWED_STATUSES = frozenset({"pending", "partial"})


def parse_and_validate_undo_manifest(payload: dict[str, Any]) -> UndoManifest:
    _require_dict(payload, "manifest root")
    schema_version = _require_int(payload, "schemaVersion")
    if schema_version != SUPPORTED_SCHEMA_VERSION:
        raise UndoManifestValidationError(
            "MANIFEST_INCOMPATIBLE",
            f"unsupported schemaVersion: {schema_version}",
        )

    sealed_at = payload.get("sealedAt")
    if not isinstance(sealed_at, str) or not sealed_at.strip():
        raise UndoManifestValidationError("MANIFEST_UNSEALED", "manifest is not sealed")

    status = payload.get("status")
    if not isinstance(status, str):
        raise UndoManifestValidationError("MANIFEST_MALFORMED", "status must be a string")
    if status not in DRY_RUN_ALLOWED_STATUSES:
        raise UndoManifestValidationError(
            "MANIFEST_NOT_ELIGIBLE",
            f"manifest status not eligible for dry-run: {status}",
        )

    source_batch_kind = payload.get("sourceBatchKind")
    if source_batch_kind != MOVE_APPLY_BATCH_KIND:
        raise UndoManifestValidationError(
            "MANIFEST_INCOMPATIBLE",
            f"unsupported sourceBatchKind: {source_batch_kind!r}",
        )

    undo_plan_id = _require_str(payload, "undoPlanId")
    run_id = _require_str(payload, "runId")
    library_id = _require_str(payload, "libraryId")
    created_at = _require_str(payload, "createdAt")
    source_preview_token = _require_str(payload, "sourcePreviewToken")
    library_revision_at_seal = _require_int(payload, "libraryRevisionAtSeal")
    run_status = _require_str(payload, "runStatus")
    idempotency_key = _require_str(payload, "idempotencyKey")

    summary = payload.get("summary")
    if not isinstance(summary, dict):
        raise UndoManifestValidationError("MANIFEST_MALFORMED", "summary must be an object")

    raw_items = payload.get("items")
    if not isinstance(raw_items, list):
        raise UndoManifestValidationError("MANIFEST_MALFORMED", "items must be a list")

    items = tuple(_parse_item(raw) for raw in raw_items)
    _reject_duplicate_operation_ids(items)

    failed_row_id = payload.get("failedRowId")
    if failed_row_id is not None and not isinstance(failed_row_id, str):
        raise UndoManifestValidationError(
            "MANIFEST_MALFORMED", "failedRowId must be string or null"
        )

    failed_error = payload.get("failedError")
    if failed_error is not None and not isinstance(failed_error, str):
        raise UndoManifestValidationError(
            "MANIFEST_MALFORMED", "failedError must be string or null"
        )

    return UndoManifest(
        schema_version=schema_version,
        undo_plan_id=undo_plan_id,
        run_id=run_id,
        library_id=library_id,
        created_at=created_at,
        sealed_at=sealed_at,
        status=status,  # type: ignore[arg-type]
        source_batch_kind=source_batch_kind,
        source_preview_token=source_preview_token,
        library_revision_at_seal=library_revision_at_seal,
        run_status=run_status,  # type: ignore[arg-type]
        summary={str(k): int(v) for k, v in summary.items() if isinstance(v, int)},
        items=items,
        idempotency_key=idempotency_key,
        failed_row_id=failed_row_id,
        failed_error=failed_error,
    )


def _parse_item(raw: Any) -> UndoManifestItem:
    if not isinstance(raw, dict):
        raise UndoManifestValidationError("MANIFEST_MALFORMED", "each item must be an object")

    operation_id = _require_str(raw, "operationId")
    sequence = _require_int(raw, "sequence")
    operation_type = _require_str(raw, "operationType")
    if operation_type != MOVE_UNDO_OPERATION_TYPE:
        raise UndoManifestValidationError(
            "MANIFEST_INCOMPATIBLE",
            f"unsupported operationType: {operation_type!r}",
        )

    undo_action = _require_str(raw, "undoAction")
    if undo_action != MOVE_UNDO_ACTION:
        raise UndoManifestValidationError(
            "MANIFEST_INCOMPATIBLE",
            f"unsupported undoAction: {undo_action!r}",
        )

    from_path = _require_str(raw, "fromPath")
    to_path = _require_str(raw, "toPath")
    backup_path = raw.get("backupPath")
    if backup_path is not None and not isinstance(backup_path, str):
        raise UndoManifestValidationError("MANIFEST_MALFORMED", "backupPath must be string or null")

    recoverability = raw.get("recoverability")
    if recoverability not in ("recoverable", "manual", "unrecoverable"):
        raise UndoManifestValidationError("MANIFEST_MALFORMED", "invalid recoverability")

    manual_required = raw.get("manualRequired")
    if not isinstance(manual_required, bool):
        raise UndoManifestValidationError("MANIFEST_MALFORMED", "manualRequired must be boolean")

    drift_policy = raw.get("driftPolicy")
    collision_policy = raw.get("collisionPolicy")
    if not isinstance(drift_policy, str) or not isinstance(collision_policy, str):
        raise UndoManifestValidationError(
            "MANIFEST_MALFORMED",
            "driftPolicy and collisionPolicy must be strings",
        )

    checkpoint_ref = raw.get("checkpointRef")
    if not isinstance(checkpoint_ref, dict):
        raise UndoManifestValidationError("MANIFEST_MALFORMED", "checkpointRef must be an object")

    return UndoManifestItem(
        operation_id=operation_id,
        sequence=sequence,
        operation_type=operation_type,
        undo_action=undo_action,  # type: ignore[arg-type]
        from_path=from_path,
        to_path=to_path,
        backup_path=backup_path,
        recoverability=recoverability,  # type: ignore[arg-type]
        manual_required=manual_required,
        drift_policy=drift_policy,
        collision_policy=collision_policy,
        checkpoint_ref={
            str(k): (v if isinstance(v, str) else None) for k, v in checkpoint_ref.items()
        },
    )


def _reject_duplicate_operation_ids(items: tuple[UndoManifestItem, ...]) -> None:
    seen: set[str] = set()
    for item in items:
        if item.operation_id in seen:
            raise UndoManifestValidationError(
                "DUPLICATE_OPERATION_ID",
                f"duplicate operationId: {item.operation_id}",
            )
        seen.add(item.operation_id)


def _require_dict(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise UndoManifestValidationError("MANIFEST_MALFORMED", f"{label} must be an object")
    return value


def _require_str(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise UndoManifestValidationError("MANIFEST_MALFORMED", f"{key} must be a non-empty string")
    return value


def _require_int(payload: dict[str, Any], key: str) -> int:
    value = payload.get(key)
    if not isinstance(value, int):
        raise UndoManifestValidationError("MANIFEST_MALFORMED", f"{key} must be an integer")
    return value
