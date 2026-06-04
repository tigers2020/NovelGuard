"""Execute frozen quality repair plan (PR-22)."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from app.bridge_contract import ApplyFailedError, RepairApplyError
from app.preview_apply_guard import PreviewApplyGuard
from app.quality_repair_guard import PendingQualityRepair, QualityRepairGuard
from application.audit_log import AuditLog
from application.encoding_detect import decode_bytes
from application.issue_selection_fingerprint import (
    issue_selection_fingerprint,
    normalize_repair_issue_ids,
)
from application.library_session import LibrarySession
from application.ports.filesystem_repair import FilesystemRepairPort
from application.repair_plan_fingerprint import repair_plan_fingerprint
from domain.apply_path_policy import resolve_under_library_root
from domain.repair_models import RepairOperation

_TEMP_SUFFIX = ".novelguard-repair.tmp"


class ApplyQualityRepairUseCase:
    def __init__(
        self,
        session: LibrarySession,
        move_guard: PreviewApplyGuard,
        repair_guard: QualityRepairGuard,
        audit: AuditLog,
        filesystem: FilesystemRepairPort,
    ) -> None:
        self._session = session
        self._move_guard = move_guard
        self._repair_guard = repair_guard
        self._audit = audit
        self._filesystem = filesystem

    def execute(
        self,
        *,
        issue_ids: list[str],
        repair_preview_token: str,
        library_revision_at_validate: int,
    ) -> None:
        token = self._validate_repair_request(repair_preview_token)
        pending, operations = self._load_validated_repair_plan(
            token=token,
            issue_ids=issue_ids,
            library_revision_at_validate=library_revision_at_validate,
        )

        root = self._session.library_root_path()
        if root is None or not operations:
            self._finish_empty(token)
            return

        self._session.set_apply_in_progress(True)
        try:
            self._apply_repair_operations(
                root=root,
                pending=pending,
                token=token,
                operations=operations,
            )
        finally:
            self._session.set_apply_in_progress(False)

    def _validate_repair_request(self, repair_preview_token: str) -> str:
        if self._session.is_apply_or_scan_busy():
            raise RepairApplyError("LIBRARY_BUSY")
        if self._move_guard.get() is not None:
            raise RepairApplyError("MOVE_PREVIEW_ACTIVE")
        token = repair_preview_token.strip()
        if not token:
            raise RepairApplyError("MISSING_REPAIR_PREVIEW_TOKEN")
        return token

    def _load_validated_repair_plan(
        self,
        *,
        token: str,
        issue_ids: list[str],
        library_revision_at_validate: int,
    ) -> tuple[PendingQualityRepair, list[RepairOperation]]:
        pending = self._repair_guard.get_by_token(token)
        if not pending:
            raise RepairApplyError("NO_PENDING_REPAIR")

        normalized = normalize_repair_issue_ids(issue_ids)
        fingerprint = issue_selection_fingerprint(normalized)
        if fingerprint != pending.fingerprint:
            self._clear_repair_pending()
            raise RepairApplyError("ISSUE_SELECTION_CHANGED")

        operations = self._repair_guard.load_operations(pending)
        if repair_plan_fingerprint(operations) != pending.plan_fingerprint:
            self._clear_repair_pending()
            raise RepairApplyError("PLAN_MISMATCH")

        revision = self._session.library_revision()
        if revision != library_revision_at_validate or revision != pending.library_revision:
            self._clear_repair_pending()
            raise RepairApplyError("STALE_REPAIR_PREVIEW")

        return pending, operations

    def _apply_repair_operations(
        self,
        *,
        root: Path,
        pending: PendingQualityRepair,
        token: str,
        operations: list[RepairOperation],
    ) -> None:
        succeeded = 0
        failed_issue_id: str | None = None
        error_message: str | None = None
        succeeded_file_ids: list[str] = []

        self._audit.append(
            "repair_started",
            repairPreviewToken=token,
            sessionId=pending.session_id,
            libraryRevision=pending.library_revision,
        )

        for op in operations:
            if self._check_drift(root, op):
                self._clear_repair_pending()
                raise RepairApplyError("STALE_REPAIR_PREVIEW")

            result = self._apply_operation(
                root=root,
                op=op,
                session_id=pending.session_id,
                token=token,
            )
            if result["outcome"] != "ok":
                failed_issue_id = op.issue_id
                error_message = result.get("error") or "repair failed"
                self._audit.append(
                    "repair_failed",
                    repairPreviewToken=token,
                    issueId=op.issue_id,
                    fileId=op.file_id,
                    outcome="error",
                    error=error_message,
                )
                break

            succeeded += 1
            succeeded_file_ids.append(op.file_id)
            self._audit.append(
                "repair_applied",
                repairPreviewToken=token,
                issueId=op.issue_id,
                fileId=op.file_id,
                relativePath=op.relative_path,
                sourceEncoding=op.source_encoding,
                backupPath=str(result.get("backupPath", "")),
                outcome="ok",
            )

        if succeeded >= 1:
            self._session.reanalyze_quality_for_file_ids(succeeded_file_ids)
            self._session.increment_library_revision()

        if failed_issue_id is not None:
            self._audit.append(
                "repair_failed",
                repairPreviewToken=token,
                failedIssueId=failed_issue_id,
                partialSuccess=succeeded > 0,
                succeededCount=succeeded,
            )
            self._clear_repair_pending()
            raise ApplyFailedError(
                "REPAIR_FAILED",
                error_message or "repair failed",
                details={
                    "partialSuccess": succeeded > 0,
                    "succeededCount": succeeded,
                    "failedIssueId": failed_issue_id,
                },
            )

        self._audit.append(
            "repair_completed",
            repairPreviewToken=token,
            operationCount=succeeded,
        )
        self._clear_repair_pending()

    def _apply_operation(
        self,
        *,
        root: Path,
        op: RepairOperation,
        session_id: str,
        token: str,
    ) -> dict[str, Any]:
        src, reason = resolve_under_library_root(root, op.relative_path)
        if reason or src is None or not src.is_file():
            return {"outcome": "error", "error": reason or "source not found"}

        try:
            original_bytes = self._filesystem.read_bytes(src)
        except OSError as exc:
            return {"outcome": "error", "error": str(exc)}

        if _hash_bytes(original_bytes) != op.source_content_hash:
            return {"outcome": "error", "error": "content drift"}

        try:
            text = decode_bytes(original_bytes, op.source_encoding)
        except UnicodeDecodeError as exc:
            return {"outcome": "error", "error": str(exc)}

        backup_dir = self._session.repair_backup_root() / session_id / op.file_id
        backup_result = self._filesystem.backup_original(
            backup_dir,
            original_bytes=original_bytes,
            metadata={
                "fileId": op.file_id,
                "originalPath": op.relative_path,
                "sourceEncoding": op.source_encoding,
                "encodingConfidence": op.encoding_confidence,
                "sourceSize": op.source_size,
                "sourceMtimeNs": op.source_mtime_ns,
                "repairPreviewToken": token,
            },
        )
        if backup_result.outcome != "ok":
            return {"outcome": "error", "error": backup_result.error or "backup failed"}

        write_result = self._filesystem.write_utf8_atomic(
            src,
            text,
            temp_suffix=_TEMP_SUFFIX,
        )
        if write_result.outcome != "ok":
            return {"outcome": "error", "error": write_result.error or "write failed"}

        return {"outcome": "ok", "backupPath": str(backup_dir)}

    def _check_drift(self, root: Path, op: RepairOperation) -> bool:
        src, reason = resolve_under_library_root(root, op.relative_path)
        if reason or src is None or not src.is_file():
            return True
        try:
            data = self._filesystem.read_bytes(src)
        except OSError:
            return True
        if len(data) != op.source_size:
            return True
        return _hash_bytes(data) != op.source_content_hash

    def _clear_repair_pending(self) -> None:
        self._repair_guard.clear()
        self._session.set_has_pending_quality_repair(False)

    def _finish_empty(self, token: str) -> None:
        self._audit.append("repair_completed", repairPreviewToken=token, operationCount=0)
        self._clear_repair_pending()


def _hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
