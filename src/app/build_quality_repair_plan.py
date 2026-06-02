"""Build frozen quality repair preview plan (PR-22)."""

from __future__ import annotations

import hashlib
from typing import Any
from uuid import uuid4

from app.bridge_contract import RepairPreviewError
from app.preview_apply_guard import PreviewApplyGuard
from app.quality_repair_guard import QualityRepairGuard
from application.audit_log import AuditLog
from application.encoding_detect import detect_source_encoding
from application.issue_selection_fingerprint import (
    MAX_REPAIR_BATCH,
    issue_selection_fingerprint,
    normalize_repair_issue_ids,
)
from application.library_session import LibrarySession
from domain.repair_models import RepairOperation


class BuildQualityRepairPlanUseCase:
    def __init__(
        self,
        session: LibrarySession,
        move_guard: PreviewApplyGuard,
        repair_guard: QualityRepairGuard,
        audit: AuditLog,
    ) -> None:
        self._session = session
        self._move_guard = move_guard
        self._repair_guard = repair_guard
        self._audit = audit

    def execute(self, request: dict[str, Any]) -> dict[str, Any]:
        if self._session.is_apply_or_scan_busy():
            raise RepairPreviewError("LIBRARY_BUSY")
        if self._move_guard.get() is not None:
            raise RepairPreviewError("MOVE_PREVIEW_ACTIVE")

        raw_ids = request.get("issueIds")
        if not isinstance(raw_ids, list):
            raise RepairPreviewError("EMPTY_SELECTION")
        if len(raw_ids) < 1:
            raise RepairPreviewError("EMPTY_SELECTION")
        if len(raw_ids) > MAX_REPAIR_BATCH:
            raise RepairPreviewError("BATCH_LIMIT_EXCEEDED")

        normalized = normalize_repair_issue_ids([str(item) for item in raw_ids])
        if len(normalized) != len(raw_ids):
            raise RepairPreviewError("MIXED_OR_INELIGIBLE_SELECTION")

        operations, rows = self._build_operations(normalized)
        if len(operations) != len(normalized):
            raise RepairPreviewError("MIXED_OR_INELIGIBLE_SELECTION")

        token = f"repair-preview-{uuid4()}"
        fingerprint = issue_selection_fingerprint(normalized)
        revision = self._session.library_revision()
        session_id = self._session.repair_session_id()

        self._repair_guard.store(
            token=token,
            session_id=session_id,
            fingerprint=fingerprint,
            library_revision=revision,
            operations=operations,
        )
        self._session.set_has_pending_quality_repair(True)

        self._audit.append(
            "repair_preview_created",
            repairPreviewToken=token,
            sessionId=session_id,
            libraryRevision=revision,
            operationCount=len(operations),
        )

        return {
            "repairPreviewToken": token,
            "libraryRevision": revision,
            "issueSelectionFingerprint": fingerprint,
            "hasPendingQualityRepair": True,
            "rows": rows,
            "summary": {
                "issueCount": len(normalized),
                "operationCount": len(operations),
            },
        }

    def _build_operations(
        self, issue_ids: list[str]
    ) -> tuple[list[RepairOperation], list[dict[str, Any]]]:
        root = self._session.library_root_path()
        if root is None:
            return [], []

        quality_issues = {issue.issue_id: issue for issue in self._session.quality_issues()}
        operations: list[RepairOperation] = []
        rows: list[dict[str, Any]] = []

        for bridge_id in issue_ids:
            domain_id = bridge_id[len("quality:") :]
            issue = quality_issues.get(domain_id)
            if issue is None or issue.kind != "invalid_utf8":
                return [], []

            record = self._session.file_record_for_quality_issue(issue)
            if record is None:
                return [], []

            path = root / record.relative_path
            try:
                data = path.read_bytes()
            except OSError:
                return [], []

            detection = detect_source_encoding(data)
            if detection is None:
                return [], []

            content_hash = _hash_bytes(data)
            op = RepairOperation(
                issue_id=bridge_id,
                file_id=record.id,
                action="utf8_convert",
                relative_path=record.relative_path,
                source_encoding=detection.encoding,
                encoding_confidence=detection.confidence,
                source_size=len(data),
                source_content_hash=content_hash,
                source_mtime_ns=record.modified_at_ns,
            )
            operations.append(op)
            row: dict[str, Any] = {
                "issueId": bridge_id,
                "action": "utf8_convert",
                "relativePath": record.relative_path,
                "sourceEncoding": detection.encoding,
                "encodingConfidence": detection.confidence,
            }
            if detection.warning:
                row["encodingWarning"] = detection.warning
            rows.append(row)

        return operations, rows


def _hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
