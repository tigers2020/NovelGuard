"""Execute immutable preview plan with real filesystem moves."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.bridge_contract import ApplyFailedError, PreviewApplyError
from app.preview_apply_guard import PreviewApplyGuard
from application.audit_log import AuditLog
from application.library_session import LibrarySession
from application.move_source_hash import content_hash_for_move
from application.plan_fingerprint import plan_fingerprint
from application.ports.filesystem_apply import FilesystemApplyPort
from domain.apply_path_policy import (
    DEFAULT_MOVE_DUPLICATE_FOLDER,
    resolve_duplicate_destination_path,
    resolve_under_library_root,
)


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
                drift_reason = self._check_drift_reason(root, op)
                if drift_reason:
                    self._guard.clear()
                    self._session.set_has_pending_apply(False)
                    if drift_reason == "destination_exists":
                        raise PreviewApplyError(
                            "DESTINATION_EXISTS",
                            f"이동 대상에 이미 파일이 있습니다: {op.dest_path}",
                        )
                    if drift_reason == "source_missing":
                        raise PreviewApplyError(
                            "STALE_PREVIEW",
                            f"원본 파일을 찾을 수 없습니다: {op.source_path}",
                        )
                    raise PreviewApplyError(
                        "STALE_PREVIEW",
                        f"미리보기 이후 파일이 변경되었습니다: {op.source_path}",
                    )

                src, src_reason = resolve_under_library_root(root, op.source_path)
                dest, dest_reason = resolve_duplicate_destination_path(
                    root, DEFAULT_MOVE_DUPLICATE_FOLDER, op.dest_path
                )
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
                    self._session.refresh_index_from_disk()
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

    def _check_drift_reason(self, root: Path, op: Any) -> str | None:
        src, reason = resolve_under_library_root(root, op.source_path)
        if reason or src is None or not src.is_file():
            return "source_missing"
        try:
            current_hash = content_hash_for_move(src, size_bytes=op.source_size)
        except OSError:
            return "source_missing"
        if current_hash != op.source_content_hash:
            return "source_changed"
        if src.stat().st_size != op.source_size:
            return "source_changed"
        dest, dest_reason = resolve_duplicate_destination_path(
            root, DEFAULT_MOVE_DUPLICATE_FOLDER, op.dest_path
        )
        if dest_reason or dest is None:
            return "invalid_path"
        if self._filesystem.file_exists(dest):
            return "destination_exists"
        return None
