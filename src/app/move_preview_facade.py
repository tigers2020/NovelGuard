"""Move preview apply/discard orchestration (PR-30 facade)."""

from __future__ import annotations

from typing import Any

from app.apply_resolved_actions import ApplyResolvedActionsUseCase
from app.bridge_contract import PreviewApplyError, validate_selection_scope
from app.preview_apply_guard import PreviewApplyGuard
from app.selection_fingerprint import selection_fingerprint
from application.library_session import LibrarySession


class MovePreviewFacade:
    def __init__(
        self,
        session: LibrarySession,
        guard: PreviewApplyGuard,
        apply_use_case: ApplyResolvedActionsUseCase,
    ) -> None:
        self._session = session
        self._guard = guard
        self._apply_use_case = apply_use_case

    def _invalidate_pending_apply(self) -> None:
        self._guard.clear()
        self._session.set_has_pending_apply(False)

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
        self._apply_use_case.execute(preview_token=token, library_revision_at_validate=revision)

    def discard_move_preview(self, payload: dict[str, Any]) -> None:
        token = (payload.get("previewToken") or "").strip()
        pending = self._guard.get()
        if pending and token and token == pending.token:
            self._guard.clear()
        self._session.set_has_pending_apply(False)

    def invalidate_on_review_update(self) -> None:
        self._invalidate_pending_apply()
