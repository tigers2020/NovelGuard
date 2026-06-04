"""Execute immutable preview plan with real filesystem moves."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.bridge_contract import ApplyFailedError, PreviewApplyError
from app.preview_apply_guard import PreviewApplyGuard
from application.audit_log import AuditLog
from application.library_session import LibrarySession
from application.plan_fingerprint import plan_fingerprint
from application.ports.filesystem_apply import FilesystemApplyPort
from domain.apply_path_policy import (
    resolve_apply_destination,
    resolve_under_library_root,
)
from domain.duplicate_content_variant import is_head_tail_variant_group_id
from infrastructure.content_hasher import head_tail_apply_hash, library_content_hash


class ApplyResolvedActionsUseCase:
    def __init__(
        self,
        session: LibrarySession,
        guard: PreviewApplyGuard,
        audit: AuditLog,
        filesystem: FilesystemApplyPort,
    ) -> None:
        self._session = session
        self._guard = guard
        self._audit = audit
        self._filesystem = filesystem

    def execute(self, *, preview_token: str, library_revision_at_validate: int) -> None:
        if self._session.is_apply_or_scan_busy():
            raise PreviewApplyError("LIBRARY_BUSY")

        pending = self._guard.get_by_token(preview_token)
        if not pending:
            raise PreviewApplyError("NO_PENDING_APPLY")

        operations = self._guard.load_operations(pending)
        if plan_fingerprint(operations) != pending.plan_fingerprint:
            self._guard.clear()
            self._session.set_has_pending_apply(False)
            raise PreviewApplyError("STALE_PREVIEW")

        if self._session.library_revision() != library_revision_at_validate:
            self._guard.clear()
            self._session.set_has_pending_apply(False)
            raise PreviewApplyError("STALE_PREVIEW")

        rows_by_id = {
            row["id"]: row for row in self._session.review_rows_snapshot() if row.get("id")
        }
        root = self._session.library_root_path()
        if root is None:
            self._finish_empty()
            return

        if not operations:
            self._finish_empty()
            return

        self._session.set_apply_in_progress(True)
        succeeded = 0
        failed_row_id: str | None = None
        error_message: str | None = None

        try:
            self._audit.append(
                "apply_started",
                previewToken=preview_token,
                libraryRevision=pending.library_revision,
            )

            for op in operations:
                row = rows_by_id.get(op.row_id)
                drift = self._check_drift(root, op, row)
                if drift:
                    self._guard.clear()
                    self._session.set_has_pending_apply(False)
                    raise PreviewApplyError("STALE_PREVIEW")

                src, src_reason = resolve_under_library_root(root, op.source_path)
                dest, dest_reason = resolve_apply_destination(root, op.dest_path)
                if src_reason or dest is None or src is None:
                    failed_row_id = op.row_id
                    error_message = src_reason or dest_reason or "invalid path"
                    self._audit.append(
                        "apply_row",
                        previewToken=preview_token,
                        rowId=op.row_id,
                        action=op.action,
                        source=op.source_path,
                        dest=op.dest_path,
                        outcome="error",
                        error=error_message,
                    )
                    break

                if self._filesystem.file_exists(dest):
                    failed_row_id = op.row_id
                    error_message = "destination exists"
                    self._audit.append(
                        "apply_row",
                        previewToken=preview_token,
                        rowId=op.row_id,
                        action=op.action,
                        source=op.source_path,
                        dest=op.dest_path,
                        outcome="error",
                        error=error_message,
                    )
                    break

                move_result = self._filesystem.move_file(src, dest)
                if move_result.outcome != "ok":
                    failed_row_id = op.row_id
                    error_message = move_result.error or "move failed"
                    self._audit.append(
                        "apply_row",
                        previewToken=preview_token,
                        rowId=op.row_id,
                        action=op.action,
                        source=op.source_path,
                        dest=op.dest_path,
                        outcome="error",
                        error=error_message,
                    )
                    break

                succeeded += 1
                self._audit.append(
                    "apply_row",
                    previewToken=preview_token,
                    rowId=op.row_id,
                    action=op.action,
                    source=op.source_path,
                    dest=op.dest_path,
                    outcome="ok",
                )

            if succeeded >= 1:
                self._session.increment_library_revision()
                try:
                    self._session.refresh_index_from_disk(after_apply=True)
                except Exception as exc:
                    self._audit.append(
                        "apply_failed",
                        previewToken=preview_token,
                        error=f"refresh failed after move: {exc}",
                        partialSuccess=True,
                        succeededCount=succeeded,
                    )
                    self._guard.clear()
                    self._session.set_has_pending_apply(False)
                    raise ApplyFailedError(
                        "APPLY_FAILED",
                        f"index refresh failed after {succeeded} move(s)",
                        details={
                            "partialSuccess": True,
                            "succeededCount": succeeded,
                            "failedRowId": failed_row_id,
                            "refreshError": str(exc),
                        },
                    ) from exc

            if failed_row_id is not None:
                self._audit.append(
                    "apply_failed",
                    previewToken=preview_token,
                    failedRowId=failed_row_id,
                    partialSuccess=succeeded > 0,
                    succeededCount=succeeded,
                )
                self._guard.clear()
                self._session.set_has_pending_apply(False)
                raise ApplyFailedError(
                    "APPLY_FAILED",
                    error_message or "apply failed",
                    details={
                        "partialSuccess": succeeded > 0,
                        "succeededCount": succeeded,
                        "failedRowId": failed_row_id,
                    },
                )

            self._audit.append(
                "apply_completed",
                previewToken=preview_token,
                operationCount=succeeded,
            )
            self._guard.clear()
            self._session.set_has_pending_apply(False)
        finally:
            self._session.set_apply_in_progress(False)

    def _finish_empty(self) -> None:
        self._audit.append("apply_completed", operationCount=0)
        self._guard.clear()
        self._session.set_has_pending_apply(False)

    def _check_drift(self, root: Path, op: Any, row: dict[str, Any] | None) -> bool:
        src, reason = resolve_under_library_root(root, op.source_path)
        if reason or src is None or not src.is_file():
            return True
        try:
            size = src.stat().st_size
            group_id = row.get("groupId") if row else None
            if isinstance(group_id, str) and is_head_tail_variant_group_id(group_id):
                current_hash = head_tail_apply_hash(src, size_bytes=size)
            else:
                current_hash = library_content_hash(src, size_bytes=size)
        except OSError:
            return True
        if current_hash != op.source_content_hash:
            return True
        if src.stat().st_size != op.source_size:
            return True
        dest, dest_reason = resolve_apply_destination(root, op.dest_path)
        if dest_reason or dest is None:
            return True
        return self._filesystem.file_exists(dest)
