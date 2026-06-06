"""Record move-apply checkpoints and seal undo manifests (no undo execution)."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path

from application.move_source_hash import content_hash_for_move
from application.recovery_store import JsonlRecoveryStore
from domain.apply_models import PreviewOperation
from domain.recovery_models import (
    FileMetadataSnapshot,
    MoveCheckpointRecord,
    MoveRunStatus,
    UndoManifest,
    UndoManifestItem,
)


def _default_now() -> datetime:
    return datetime.now(UTC)


def _iso_z(dt: datetime) -> str:
    return dt.isoformat().replace("+00:00", "Z")


def _file_metadata(path: Path) -> FileMetadataSnapshot:
    if not path.is_file():
        return FileMetadataSnapshot(exists=False, size=None, content_hash=None, mtime_ns=None)
    stat = path.stat()
    size = stat.st_size
    return FileMetadataSnapshot(
        exists=True,
        size=size,
        content_hash=content_hash_for_move(path, size_bytes=size),
        mtime_ns=stat.st_mtime_ns,
    )


def _before_from_operation(op: PreviewOperation) -> FileMetadataSnapshot:
    return FileMetadataSnapshot(
        exists=True,
        size=op.source_size,
        content_hash=op.source_content_hash,
        mtime_ns=op.source_mtime_ns,
    )


def classify_move_run_status(*, succeeded: int, failed_row_id: str | None) -> MoveRunStatus:
    if failed_row_id is None:
        return "completed"
    if succeeded > 0:
        return "partially_applied"
    return "failed"


class MoveApplyRecoveryRun:
    def __init__(
        self,
        store: JsonlRecoveryStore,
        *,
        library_id: str,
        preview_token: str,
        library_revision_at_start: int,
        job_id: str | None = None,
        now_fn: Callable[[], datetime] | None = None,
    ) -> None:
        self._store = store
        self._library_id = library_id
        self._preview_token = preview_token
        self._library_revision_at_start = library_revision_at_start
        self._job_id = job_id
        self._now_fn = now_fn or _default_now
        self._run_id = str(uuid.uuid4())
        self._created_at = _iso_z(self._now_fn())
        self._checkpoints: list[MoveCheckpointRecord] = []
        self._sequence = 0

    @property
    def run_id(self) -> str:
        return self._run_id

    def record_applied(
        self,
        op: PreviewOperation,
        *,
        dest_path: Path,
        library_revision_after: int | None = None,
    ) -> str:
        self._sequence += 1
        operation_id = str(uuid.uuid4())
        after = _file_metadata(dest_path)
        record = MoveCheckpointRecord(
            schema_version=1,
            operation_id=operation_id,
            run_id=self._run_id,
            job_id=self._job_id,
            batch_kind="move_apply",
            operation_type="move_duplicate",
            library_id=self._library_id,
            library_revision_before=self._library_revision_at_start,
            library_revision_after=library_revision_after,
            preview_token=self._preview_token,
            source_path=op.source_path,
            destination_path=op.dest_path,
            backup_path=None,
            before=_before_from_operation(op),
            after=after,
            row_id=op.row_id,
            file_id=op.source_file_id,
            status="applied",
            error=None,
            created_at=_iso_z(self._now_fn()),
            sequence=self._sequence,
        )
        self._checkpoints.append(record)
        self._store.append_checkpoint(record.to_dict())
        return operation_id

    def seal(
        self,
        *,
        succeeded: int,
        failed_row_id: str | None,
        failed_error: str | None,
        library_revision_at_seal: int,
    ) -> Path:
        run_status = classify_move_run_status(
            succeeded=succeeded,
            failed_row_id=failed_row_id,
        )
        failed_count = 1 if failed_row_id is not None else 0
        manifest = build_undo_manifest(
            run_id=self._run_id,
            library_id=self._library_id,
            preview_token=self._preview_token,
            created_at=self._created_at,
            sealed_at=_iso_z(self._now_fn()),
            run_status=run_status,
            library_revision_at_seal=library_revision_at_seal,
            checkpoints=self._checkpoints,
            succeeded=succeeded,
            failed_count=failed_count,
            failed_row_id=failed_row_id,
            failed_error=failed_error,
        )
        return self._store.write_undo_manifest(manifest.to_dict())


def build_undo_manifest(
    *,
    run_id: str,
    library_id: str,
    preview_token: str,
    created_at: str,
    sealed_at: str,
    run_status: MoveRunStatus,
    library_revision_at_seal: int,
    checkpoints: list[MoveCheckpointRecord],
    succeeded: int,
    failed_count: int,
    failed_row_id: str | None,
    failed_error: str | None,
) -> UndoManifest:
    undo_plan_id = str(uuid.uuid4())
    items = tuple(_undo_item_from_checkpoint(cp) for cp in checkpoints)
    idempotency_key = _idempotency_key(run_id, checkpoints)
    return UndoManifest(
        schema_version=1,
        undo_plan_id=undo_plan_id,
        run_id=run_id,
        library_id=library_id,
        created_at=created_at,
        sealed_at=sealed_at,
        status="pending",
        source_batch_kind="move_apply",
        source_preview_token=preview_token,
        library_revision_at_seal=library_revision_at_seal,
        run_status=run_status,
        summary={
            "appliedCount": succeeded,
            "skippedCount": 0,
            "failedCount": failed_count,
            "recoverableCount": succeeded,
            "manualCount": 0,
            "unrecoverableCount": 0,
        },
        items=items,
        idempotency_key=idempotency_key,
        failed_row_id=failed_row_id,
        failed_error=failed_error,
    )


def _undo_item_from_checkpoint(cp: MoveCheckpointRecord) -> UndoManifestItem:
    return UndoManifestItem(
        operation_id=cp.operation_id,
        sequence=cp.sequence,
        operation_type=cp.operation_type,
        undo_action="move_back",
        from_path=cp.destination_path,
        to_path=cp.source_path,
        backup_path=None,
        recoverability="recoverable",
        manual_required=False,
        drift_policy="strict",
        collision_policy="block",
        checkpoint_ref={
            "beforeHash": cp.before.content_hash,
            "afterHash": cp.after.content_hash,
        },
    )


def _idempotency_key(run_id: str, checkpoints: list[MoveCheckpointRecord]) -> str:
    ordered = ",".join(cp.operation_id for cp in sorted(checkpoints, key=lambda c: c.sequence))
    payload = f"{run_id}:{ordered}"
    return sha256(payload.encode("utf-8")).hexdigest()
