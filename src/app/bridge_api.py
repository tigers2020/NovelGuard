"""pywebview js_api — thin delegation to LibrarySession."""

from __future__ import annotations

import json
from typing import Any
from uuid import uuid4

from app.bridge_contract import (
    PreviewApplyError,
    clamp_query_limit,
    validate_app_snapshot,
    validate_move_preview,
    validate_quality_rows_page,
    validate_review_rows_page,
    validate_selection_scope,
)
from app.selection_fingerprint import selection_fingerprint
from app.session_factory import create_library_session
from application.library_session import LibrarySession


class BridgeApi:
    """Expose methods to ``window.pywebview.api`` (snake_case)."""

    def __init__(self, session: LibrarySession | None = None) -> None:
        self._session = session or create_library_session()
        self._pending_apply: dict[str, Any] | None = None

    def get_snapshot(self) -> dict[str, Any]:
        payload = self._session.get_snapshot()
        validate_app_snapshot(payload)
        return payload

    def set_work_mode(self, mode: str) -> None:
        self._session.set_work_mode(mode)

    def select_folder(self) -> None:
        self._session.select_folder()

    def start_scan(self, options: dict[str, Any] | None = None) -> None:
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

    def get_duplicate_group_detail(self, group_id: str) -> dict[str, Any]:
        return self._session.get_duplicate_group_detail(group_id)

    def get_quality_issue_detail(self, issue_id: str) -> dict[str, Any]:
        return self._session.get_quality_issue_detail(issue_id)

    def get_move_preview(self, selection: dict[str, Any]) -> dict[str, Any]:
        validate_selection_scope(selection)
        token = f"preview-{uuid4()}"
        fp = selection_fingerprint(selection)
        rev = self._session.library_revision()
        self._pending_apply = {
            "token": token,
            "fingerprint": fp,
            "library_revision": rev,
        }
        self._session.set_has_pending_apply(True)
        preview_row_id = self._session.first_file_id() or "row-1"
        payload: dict[str, Any] = {
            "previewToken": token,
            "libraryRevision": rev,
            "selectionFingerprint": fp,
            "hasPendingApply": True,
            "rows": [{"id": preview_row_id, "action": "move_organized"}],
            "summary": {"rowCount": 1},
        }
        validate_move_preview(payload)
        return payload

    def _validate_apply(self, payload: dict[str, Any]) -> tuple[dict[str, Any], str]:
        token = (payload.get("previewToken") or "").strip()
        if not token:
            raise PreviewApplyError("MISSING_PREVIEW_TOKEN")
        selection = payload.get("selection")
        if not isinstance(selection, dict):
            raise PreviewApplyError("INVALID_PREVIEW_TOKEN", "selection required")
        validate_selection_scope(selection)
        pending = self._pending_apply
        if not pending:
            raise PreviewApplyError("NO_PENDING_APPLY")
        if token != pending.get("token"):
            raise PreviewApplyError("INVALID_PREVIEW_TOKEN")
        if self._session.library_revision() != pending.get("library_revision"):
            raise PreviewApplyError("STALE_PREVIEW")
        fp = selection_fingerprint(selection)
        if fp != pending.get("fingerprint"):
            raise PreviewApplyError("SELECTION_CHANGED")
        return selection, token

    def apply_resolved_actions(self, payload: dict[str, Any]) -> None:
        self._validate_apply(payload)
        self._pending_apply = None
        self._session.set_has_pending_apply(False)

    def discard_move_preview(self, payload: dict[str, Any]) -> None:
        token = (payload.get("previewToken") or "").strip()
        pending = self._pending_apply
        if pending and token and token == pending.get("token"):
            self._pending_apply = None
        self._session.set_has_pending_apply(False)

    def query_review_rows_json(self, query_json: str) -> str:
        """Optional helper if JS passes JSON string."""
        return json.dumps(self.query_review_rows(json.loads(query_json)))
