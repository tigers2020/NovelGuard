"""Build real move preview plan from library session + selection."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import uuid4

from app.bridge_contract import PreviewApplyError
from app.preview_apply_guard import PreviewApplyGuard
from app.quality_repair_guard import QualityRepairGuard
from app.selection_fingerprint import selection_fingerprint
from app.selection_resolve import resolve_selection_rows
from application.audit_log import AuditLog
from application.library_session import LibrarySession
from application.ports.filesystem_apply import FilesystemApplyPort
from domain.apply_models import PreviewOperation
from domain.apply_path_policy import (
    build_move_duplicate_dest_relative,
    resolve_destination_path,
    validate_move_operation,
)
from domain.models import FileRecord
from infrastructure.content_hasher import hash_file


class BuildPreviewPlanUseCase:
    def __init__(
        self,
        session: LibrarySession,
        guard: PreviewApplyGuard,
        repair_guard: QualityRepairGuard,
        audit: AuditLog,
        filesystem: FilesystemApplyPort,
    ) -> None:
        self._session = session
        self._guard = guard
        self._repair_guard = repair_guard
        self._audit = audit
        self._filesystem = filesystem

    def execute(self, selection: dict[str, Any]) -> dict[str, Any]:
        if self._repair_guard.get() is not None:
            raise PreviewApplyError("REPAIR_PREVIEW_ACTIVE")
        root = self._session.library_root_path()
        if root is None:
            return self._empty_preview(selection)

        selected_rows = resolve_selection_rows(self._session.review_rows_snapshot(), selection)
        operations: list[PreviewOperation] = []
        preview_rows: list[dict[str, str]] = []
        conflict_count = 0
        blocked_count = 0

        for row in selected_rows:
            if row.get("rowKind") != "file":
                continue
            status = row.get("status")
            if status != "approved":
                continue
            action = row.get("proposedAction")
            if action != "move_duplicate":
                continue

            file_record = self._session.file_record_for_review_row(row)
            if file_record is None:
                conflict_count += 1
                continue

            target_folder = row.get("targetFolder") or "duplicate"
            dest_rel = build_move_duplicate_dest_relative(target_folder, file_record.name)
            dest_abs, _ = resolve_destination_path(root, dest_rel)
            dest_exists = bool(dest_abs and self._filesystem.file_exists(dest_abs))

            op = PreviewOperation(
                row_id=str(row["id"]),
                action="move_duplicate",
                source_path=file_record.relative_path,
                dest_path=dest_rel,
                source_file_id=file_record.id,
                source_size=file_record.size_bytes,
                source_content_hash=self._content_hash(root, file_record),
                source_mtime_ns=file_record.modified_at_ns,
            )
            policy = validate_move_operation(root, op, destination_exists=dest_exists)
            if not policy.allowed:
                if policy.reason == "destination_exists":
                    conflict_count += 1
                else:
                    blocked_count += 1
                continue

            operations.append(op)
            preview_rows.append({"id": op.row_id, "action": "move_duplicate"})

        token = f"preview-{uuid4()}"
        fingerprint = selection_fingerprint(selection)
        revision = self._session.library_revision()

        self._guard.store(
            token=token,
            fingerprint=fingerprint,
            library_revision=revision,
            operations=operations,
        )
        self._session.set_has_pending_apply(True)

        summary: dict[str, Any] = {
            "rowCount": len(preview_rows),
            "operationCount": len(operations),
        }
        if conflict_count:
            summary["conflictCount"] = conflict_count
        if blocked_count:
            summary["blockedCount"] = blocked_count

        self._audit.append(
            "preview_built",
            previewToken=token,
            libraryRevision=revision,
            operationCount=len(operations),
        )

        return {
            "previewToken": token,
            "libraryRevision": revision,
            "selectionFingerprint": fingerprint,
            "hasPendingApply": True,
            "rows": preview_rows,
            "summary": summary,
        }

    def _empty_preview(self, selection: dict[str, Any]) -> dict[str, Any]:
        token = f"preview-{uuid4()}"
        fingerprint = selection_fingerprint(selection)
        revision = self._session.library_revision()
        self._guard.store(
            token=token,
            fingerprint=fingerprint,
            library_revision=revision,
            operations=[],
        )
        self._session.set_has_pending_apply(True)
        self._audit.append(
            "preview_built",
            previewToken=token,
            libraryRevision=revision,
            operationCount=0,
        )
        return {
            "previewToken": token,
            "libraryRevision": revision,
            "selectionFingerprint": fingerprint,
            "hasPendingApply": True,
            "rows": [],
            "summary": {"rowCount": 0, "operationCount": 0},
        }

    def _content_hash(self, root: Path, file_record: FileRecord) -> str:
        if file_record.content_sha256:
            return file_record.content_sha256
        return hash_file(root / file_record.relative_path)
