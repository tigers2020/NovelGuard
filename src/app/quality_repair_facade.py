"""Quality repair apply/discard orchestration (PR-30 facade)."""

from __future__ import annotations

from typing import Any

from app.apply_quality_repair import ApplyQualityRepairUseCase
from app.bridge_contract import RepairApplyError
from app.quality_repair_guard import QualityRepairGuard
from application.issue_selection_fingerprint import issue_selection_fingerprint
from application.library_session import LibrarySession


class QualityRepairFacade:
    def __init__(
        self,
        session: LibrarySession,
        guard: QualityRepairGuard,
        apply_use_case: ApplyQualityRepairUseCase,
    ) -> None:
        self._session = session
        self._guard = guard
        self._apply_use_case = apply_use_case

    def _invalidate_pending_repair(self) -> None:
        self._guard.clear()
        self._session.set_has_pending_quality_repair(False)

    def _validate_repair_apply(self, payload: dict[str, Any]) -> tuple[list[str], str, int]:
        token = (payload.get("repairPreviewToken") or "").strip()
        if not token:
            raise RepairApplyError("MISSING_REPAIR_PREVIEW_TOKEN")
        issue_ids = payload.get("issueIds")
        if not isinstance(issue_ids, list) or not issue_ids:
            raise RepairApplyError("ISSUE_SELECTION_CHANGED", "issueIds required")
        pending = self._guard.get()
        if not pending:
            raise RepairApplyError("NO_PENDING_REPAIR")
        if token != pending.token:
            raise RepairApplyError("INVALID_REPAIR_PREVIEW_TOKEN")
        if self._session.library_revision() != pending.library_revision:
            self._invalidate_pending_repair()
            raise RepairApplyError("STALE_REPAIR_PREVIEW")
        fp = issue_selection_fingerprint([str(item) for item in issue_ids])
        if fp != pending.fingerprint:
            self._invalidate_pending_repair()
            raise RepairApplyError("ISSUE_SELECTION_CHANGED")
        return [str(item) for item in issue_ids], token, pending.library_revision

    def apply_quality_repair(self, payload: dict[str, Any]) -> None:
        issue_ids, token, revision = self._validate_repair_apply(payload)
        self._apply_use_case.execute(
            issue_ids=issue_ids,
            repair_preview_token=token,
            library_revision_at_validate=revision,
        )

    def discard_quality_repair_preview(self, payload: dict[str, Any]) -> None:
        token = (payload.get("repairPreviewToken") or "").strip()
        pending = self._guard.get()
        if pending and token and token == pending.token:
            self._guard.clear()
        self._session.set_has_pending_quality_repair(False)
