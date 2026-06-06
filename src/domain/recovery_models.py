"""Domain types for move-apply recovery checkpoints and undo manifests."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

MoveRunStatus = Literal["completed", "failed", "partially_applied"]
UndoManifestStatus = Literal["pending", "executing", "completed", "partial", "expired", "superseded"]
CheckpointItemStatus = Literal["applied", "failed", "skipped"]
Recoverability = Literal["recoverable", "manual", "unrecoverable"]
UndoAction = Literal["move_back"]


@dataclass(frozen=True, slots=True)
class FileMetadataSnapshot:
    exists: bool
    size: int | None
    content_hash: str | None
    mtime_ns: int | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "exists": self.exists,
            "size": self.size,
            "contentHash": self.content_hash,
            "mtimeNs": self.mtime_ns,
            "encoding": None,
        }


@dataclass(frozen=True, slots=True)
class MoveCheckpointRecord:
    schema_version: int
    operation_id: str
    run_id: str
    job_id: str | None
    batch_kind: str
    operation_type: str
    library_id: str
    library_revision_before: int
    library_revision_after: int | None
    preview_token: str
    source_path: str
    destination_path: str
    backup_path: str | None
    before: FileMetadataSnapshot
    after: FileMetadataSnapshot
    row_id: str
    file_id: str
    status: CheckpointItemStatus
    error: str | None
    created_at: str
    sequence: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "schemaVersion": self.schema_version,
            "operationId": self.operation_id,
            "runId": self.run_id,
            "jobId": self.job_id,
            "batchKind": self.batch_kind,
            "operationType": self.operation_type,
            "libraryId": self.library_id,
            "libraryRevisionBefore": self.library_revision_before,
            "libraryRevisionAfter": self.library_revision_after,
            "previewToken": self.preview_token,
            "repairPreviewToken": None,
            "finalizeReportId": None,
            "sourcePath": self.source_path,
            "destinationPath": self.destination_path,
            "backupPath": self.backup_path,
            "before": self.before.to_dict(),
            "after": self.after.to_dict(),
            "rowId": self.row_id,
            "issueId": None,
            "fileId": self.file_id,
            "status": self.status,
            "error": self.error,
            "createdAt": self.created_at,
            "sequence": self.sequence,
        }


@dataclass(frozen=True, slots=True)
class UndoManifestItem:
    operation_id: str
    sequence: int
    operation_type: str
    undo_action: UndoAction
    from_path: str
    to_path: str
    backup_path: str | None
    recoverability: Recoverability
    manual_required: bool
    drift_policy: str
    collision_policy: str
    checkpoint_ref: dict[str, str | None]

    def to_dict(self) -> dict[str, Any]:
        return {
            "operationId": self.operation_id,
            "sequence": self.sequence,
            "operationType": self.operation_type,
            "undoAction": self.undo_action,
            "fromPath": self.from_path,
            "toPath": self.to_path,
            "backupPath": self.backup_path,
            "recoverability": self.recoverability,
            "manualRequired": self.manual_required,
            "driftPolicy": self.drift_policy,
            "collisionPolicy": self.collision_policy,
            "checkpointRef": self.checkpoint_ref,
        }


@dataclass(frozen=True, slots=True)
class UndoManifest:
    schema_version: int
    undo_plan_id: str
    run_id: str
    library_id: str
    created_at: str
    sealed_at: str
    status: UndoManifestStatus
    source_batch_kind: str
    source_preview_token: str
    library_revision_at_seal: int
    run_status: MoveRunStatus
    summary: dict[str, int]
    items: tuple[UndoManifestItem, ...]
    idempotency_key: str
    failed_row_id: str | None
    failed_error: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "schemaVersion": self.schema_version,
            "undoPlanId": self.undo_plan_id,
            "runId": self.run_id,
            "libraryId": self.library_id,
            "createdAt": self.created_at,
            "sealedAt": self.sealed_at,
            "status": self.status,
            "sourceBatchKind": self.source_batch_kind,
            "sourcePreviewToken": self.source_preview_token,
            "libraryRevisionAtSeal": self.library_revision_at_seal,
            "runStatus": self.run_status,
            "summary": dict(self.summary),
            "items": [item.to_dict() for item in self.items],
            "idempotencyKey": self.idempotency_key,
            "failedRowId": self.failed_row_id,
            "failedError": self.failed_error,
        }
