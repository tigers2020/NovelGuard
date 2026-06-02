"""pywebview js_api — thin delegation to LibrarySession."""

from __future__ import annotations

import json
from typing import Any

from app import version
from app.apply_quality_repair import ApplyQualityRepairUseCase
from app.apply_resolved_actions import ApplyResolvedActionsUseCase
from app.bridge_contract import (
    FinalizeError,
    PreviewApplyError,
    RepairApplyError,
    clamp_query_limit,
    validate_app_info,
    validate_app_snapshot,
    validate_duplicate_group_detail,
    validate_file_rows_page,
    validate_finalize_result,
    validate_finalize_summary,
    validate_move_preview,
    validate_quality_issue_detail,
    validate_quality_repair_preview,
    validate_quality_rows_page,
    validate_review_rows_page,
    validate_selection_scope,
)
from app.build_preview_plan import BuildPreviewPlanUseCase
from app.build_quality_repair_plan import BuildQualityRepairPlanUseCase
from app.preview_apply_guard import PreviewApplyGuard
from app.quality_repair_guard import QualityRepairGuard
from app.selection_fingerprint import selection_fingerprint
from application.issue_selection_fingerprint import issue_selection_fingerprint
from application.library_session import LibrarySession
from application.review_errors import ReviewDecisionError


class BridgeApi:
    """Expose methods to ``window.pywebview.api`` (snake_case)."""

    def __init__(
        self,
        session: LibrarySession,
        *,
        guard: PreviewApplyGuard,
        repair_guard: QualityRepairGuard,
        preview_use_case: BuildPreviewPlanUseCase,
        apply_use_case: ApplyResolvedActionsUseCase,
        repair_preview_use_case: BuildQualityRepairPlanUseCase,
        repair_apply_use_case: ApplyQualityRepairUseCase,
    ) -> None:
        self._session = session
        self._guard = guard
        self._repair_guard = repair_guard
        self._preview_use_case = preview_use_case
        self._apply_use_case = apply_use_case
        self._repair_preview_use_case = repair_preview_use_case
        self._repair_apply_use_case = repair_apply_use_case

    def get_snapshot(self) -> dict[str, Any]:
        payload = self._session.get_snapshot()
        validate_app_snapshot(payload)
        return payload

    def set_work_mode(self, mode: str) -> None:
        self._session.set_work_mode(mode)

    def select_folder(self) -> None:
        if self._session.is_apply_or_scan_busy():
            raise PreviewApplyError("LIBRARY_BUSY")
        self._session.select_folder()

    def start_scan(self, options: dict[str, Any] | None = None) -> None:
        if self._session.is_apply_or_scan_busy():
            raise PreviewApplyError("LIBRARY_BUSY")
        self._session.start_scan(options)

    def cancel_run(self) -> None:
        self._session.cancel_run()

    def query_review_rows(self, query: dict[str, Any]) -> dict[str, Any]:
        _ = clamp_query_limit(query)
        payload = self._session.query_review_rows(query)
        validate_review_rows_page(payload)
        return payload

    def query_quality_rows(self, query: dict[str, Any]) -> dict[str, Any]:
        _ = clamp_query_limit(query)
        payload = self._session.query_quality_rows(query)
        validate_quality_rows_page(payload)
        return payload

    def query_file_rows(self, query: dict[str, Any]) -> dict[str, Any]:
        _ = clamp_query_limit(query)
        payload = self._session.query_file_rows(query)
        validate_file_rows_page(payload)
        return payload

    def get_duplicate_group_detail(self, group_id: str) -> dict[str, Any]:
        result = self._session.get_duplicate_group_detail(group_id)
        validate_duplicate_group_detail(result)
        return result

    def get_quality_issue_detail(self, issue_id: str) -> dict[str, Any]:
        payload = self._session.get_quality_issue_detail(issue_id)
        validate_quality_issue_detail(payload)
        return payload

    def get_quality_repair_preview(self, request: dict[str, Any]) -> dict[str, Any]:
        payload = self._repair_preview_use_case.execute(request)
        validate_quality_repair_preview(payload)
        return payload

    def get_move_preview(self, selection: dict[str, Any]) -> dict[str, Any]:
        validate_selection_scope(selection)
        payload = self._preview_use_case.execute(selection)
        validate_move_preview(payload)
        return payload

    def _invalidate_pending_apply(self) -> None:
        self._guard.clear()
        self._session.set_has_pending_apply(False)

    def _invalidate_pending_repair(self) -> None:
        self._repair_guard.clear()
        self._session.set_has_pending_quality_repair(False)

    def _validate_apply(self, payload: dict[str, Any]) -> tuple[dict[str, Any], str, int]:
        token = (payload.get("previewToken") or "").strip()
        if not token:
            raise PreviewApplyError("MISSING_PREVIEW_TOKEN")
        selection = payload.get("selection")
        if not isinstance(selection, dict):
            raise PreviewApplyError("INVALID_PREVIEW_TOKEN", "selection required")
        validate_selection_scope(selection)
        pending = self._guard.get()
        if not pending:
            raise PreviewApplyError("NO_PENDING_APPLY")
        if token != pending.token:
            raise PreviewApplyError("INVALID_PREVIEW_TOKEN")
        if self._session.library_revision() != pending.library_revision:
            self._invalidate_pending_apply()
            raise PreviewApplyError("STALE_PREVIEW")
        fp = selection_fingerprint(selection)
        if fp != pending.fingerprint:
            self._invalidate_pending_apply()
            raise PreviewApplyError("SELECTION_CHANGED")
        return selection, token, pending.library_revision

    def apply_resolved_actions(self, payload: dict[str, Any]) -> None:
        _selection, token, revision = self._validate_apply(payload)
        _ = _selection
        self._apply_use_case.execute(preview_token=token, library_revision_at_validate=revision)

    def _validate_repair_apply(self, payload: dict[str, Any]) -> tuple[list[str], str, int]:
        token = (payload.get("repairPreviewToken") or "").strip()
        if not token:
            raise RepairApplyError("MISSING_REPAIR_PREVIEW_TOKEN")
        issue_ids = payload.get("issueIds")
        if not isinstance(issue_ids, list) or not issue_ids:
            raise RepairApplyError("ISSUE_SELECTION_CHANGED", "issueIds required")
        pending = self._repair_guard.get()
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
        self._repair_apply_use_case.execute(
            issue_ids=issue_ids,
            repair_preview_token=token,
            library_revision_at_validate=revision,
        )

    def update_review_decisions(self, payload: dict[str, Any]) -> dict[str, Any]:
        if self._session.is_apply_or_scan_busy():
            raise PreviewApplyError("LIBRARY_BUSY")
        selection = payload.get("selection")
        if not isinstance(selection, dict):
            raise PreviewApplyError("INVALID_REVIEW_COMMAND", "selection required")
        validate_selection_scope(selection)
        command = payload.get("command")
        if not isinstance(command, str) or not command.strip():
            raise PreviewApplyError("INVALID_REVIEW_COMMAND", "command required")
        keeper_file_id = payload.get("keeperFileId")
        if keeper_file_id is not None and not isinstance(keeper_file_id, str):
            raise PreviewApplyError("INVALID_REVIEW_COMMAND", "keeperFileId must be a string")
        try:
            result = self._session.update_review_decisions(
                selection,
                command.strip(),
                keeper_file_id=keeper_file_id,
            )
        except ReviewDecisionError as exc:
            raise PreviewApplyError(exc.reason, str(exc)) from exc
        if result.get("updatedCount", 0) > 0:
            self._invalidate_pending_apply()
        return result

    def get_app_info(self) -> dict[str, Any]:
        payload = version.get_app_info()
        validate_app_info(payload)
        return payload

    def get_app_setting(self, key: str) -> bool:
        return self._session.get_app_setting(key)

    def set_app_setting(self, key: str, value: bool) -> None:
        self._session.set_app_setting(key, value)

    def discard_move_preview(self, payload: dict[str, Any]) -> None:
        token = (payload.get("previewToken") or "").strip()
        pending = self._guard.get()
        if pending and token and token == pending.token:
            self._guard.clear()
        self._session.set_has_pending_apply(False)

    def discard_quality_repair_preview(self, payload: dict[str, Any]) -> None:
        token = (payload.get("repairPreviewToken") or "").strip()
        pending = self._repair_guard.get()
        if pending and token and token == pending.token:
            self._repair_guard.clear()
        self._session.set_has_pending_quality_repair(False)

    def query_review_rows_json(self, query_json: str) -> str:
        """Optional helper if JS passes JSON string."""
        return json.dumps(self.query_review_rows(json.loads(query_json)))

    def get_finalize_summary(self) -> dict[str, Any]:
        if not self._session.library_root_path():
            raise FinalizeError("NO_LIBRARY")
        payload = self._session.get_finalize_summary()
        validate_finalize_summary(payload)
        return payload

    def run_finalize_verification(self, request: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(request, dict):
            raise FinalizeError("INVALID_REQUEST", "request must be a dict")
        try:
            payload = self._session.run_finalize_verification(request)
        except RuntimeError as exc:
            reason = str(exc)
            if reason in ("NO_LIBRARY", "LIBRARY_BUSY", "FINALIZE_NOT_CONFIGURED"):
                raise FinalizeError(reason) from exc
            raise
        validate_finalize_result(payload)
        return payload

    def get_finalize_report(self, report_id: str) -> dict[str, Any]:
        if not isinstance(report_id, str) or not report_id.strip():
            raise FinalizeError("INVALID_REQUEST", "reportId required")
        try:
            return self._session.read_finalize_report(None, report_id.strip())
        except FileNotFoundError as exc:
            raise FinalizeError("REPORT_NOT_FOUND") from exc

    def cancel_finalize(self) -> None:
        self._session.cancel_finalize()
