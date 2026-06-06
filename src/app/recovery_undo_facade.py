"""Bridge-facing recovery undo orchestration (preview guard + planner + executor)."""

from __future__ import annotations

import uuid
from typing import Any

from app.bridge_contract import RecoveryError
from app.undo_preview_guard import UndoPreviewGuard
from application.library_session import LibrarySession
from application.recovery_state import build_recovery_state, empty_recovery_state
from application.recovery_store import JsonlRecoveryStore
from application.undo_dry_run_planner import plan_move_undo_from_store
from application.undo_manifest_errors import UndoExecutionError, UndoManifestValidationError
from application.undo_move_executor import execute_move_undo_from_store
from domain.recovery_models import UndoDryRunPlan
from infrastructure.local_filesystem_apply import LocalFilesystemApplyAdapter


def _map_validation_error(exc: UndoManifestValidationError) -> RecoveryError:
    code_map = {
        "MANIFEST_NOT_FOUND": "UNDO_PLAN_NOT_FOUND",
        "MANIFEST_UNSEALED": "UNDO_BLOCKED",
        "MANIFEST_NOT_ELIGIBLE": "UNDO_BLOCKED",
        "MANIFEST_INCOMPATIBLE": "UNDO_BLOCKED",
        "MANIFEST_MALFORMED": "UNDO_BLOCKED",
        "DUPLICATE_OPERATION_ID": "UNDO_BLOCKED",
    }
    return RecoveryError(code_map.get(exc.code, "UNDO_BLOCKED"), exc.message)


def _map_execution_error(exc: UndoExecutionError) -> RecoveryError:
    code_map = {
        "PLAN_REQUIRED": "NO_PENDING_UNDO_PREVIEW",
        "PLAN_MANIFEST_MISMATCH": "STALE_UNDO_PREVIEW",
        "MANIFEST_NOT_ELIGIBLE": "UNDO_IN_PROGRESS",
    }
    return RecoveryError(code_map.get(exc.code, "UNDO_BLOCKED"), exc.message)


class RecoveryUndoFacade:
    def __init__(
        self,
        session: LibrarySession,
        store: JsonlRecoveryStore,
        guard: UndoPreviewGuard,
        *,
        filesystem: LocalFilesystemApplyAdapter | None = None,
    ) -> None:
        self._session = session
        self._store = store
        self._guard = guard
        self._filesystem = filesystem

    def get_recovery_state(self) -> dict[str, Any]:
        if self._session.library_root_path() is None:
            return empty_recovery_state()
        return build_recovery_state(
            store=self._store,
            library_id=self._session.library_id(),
        )

    def preview_undo_plan(self, request: dict[str, Any]) -> dict[str, Any]:
        if self._session.is_apply_or_scan_busy():
            raise RecoveryError("LIBRARY_BUSY")

        library_root = self._session.library_root_path()
        if library_root is None:
            raise RecoveryError("NO_LIBRARY")

        undo_plan_id = _require_undo_plan_id(request)
        raw = _read_manifest_raw(self._store, undo_plan_id)

        status = raw.get("status")
        if status == "executing":
            raise RecoveryError("UNDO_IN_PROGRESS")

        if raw.get("libraryId") != self._session.library_id():
            raise RecoveryError("UNDO_PLAN_NOT_FOUND")

        plan = _build_preview_plan(
            library_root=library_root,
            store=self._store,
            undo_plan_id=undo_plan_id,
            raw=raw,
        )

        token = str(uuid.uuid4())
        self._guard.store(
            token=token,
            undo_plan_id=undo_plan_id,
            library_id=self._session.library_id(),
            plan=plan,
        )
        payload = plan.to_dict()
        payload["previewToken"] = token
        return payload

    def execute_undo_plan(self, request: dict[str, Any]) -> dict[str, Any]:
        if self._session.is_apply_or_scan_busy():
            raise RecoveryError("LIBRARY_BUSY")

        library_root = self._session.library_root_path()
        if library_root is None:
            raise RecoveryError("NO_LIBRARY")

        undo_plan_id = _require_undo_plan_id(request)
        preview_token = (request.get("previewToken") or "").strip()
        if not preview_token:
            raise RecoveryError("MISSING_PREVIEW_TOKEN")

        pending = self._guard.get()
        if pending is None:
            raise RecoveryError("NO_PENDING_UNDO_PREVIEW")
        if pending.token != preview_token or pending.undo_plan_id != undo_plan_id:
            raise RecoveryError("INVALID_PREVIEW_TOKEN")
        if pending.library_id != self._session.library_id():
            raise RecoveryError("STALE_UNDO_PREVIEW")

        try:
            result = execute_move_undo_from_store(
                library_root=library_root,
                store=self._store,
                plan=pending.plan,
                filesystem=self._filesystem,
            )
        except UndoExecutionError as exc:
            raise _map_execution_error(exc) from exc
        finally:
            self._guard.clear()

        return result.to_dict()


def _require_undo_plan_id(request: dict[str, Any]) -> str:
    undo_plan_id = (request.get("undoPlanId") or "").strip()
    if not undo_plan_id:
        raise RecoveryError("INVALID_REQUEST", "undoPlanId required")
    return undo_plan_id


def _read_manifest_raw(store: JsonlRecoveryStore, undo_plan_id: str) -> dict[str, Any]:
    try:
        return store.read_undo_manifest_raw(undo_plan_id)
    except UndoManifestValidationError as exc:
        raise _map_validation_error(exc) from exc


def _build_preview_plan(
    *,
    library_root,
    store: JsonlRecoveryStore,
    undo_plan_id: str,
    raw: dict[str, Any],
) -> UndoDryRunPlan:
    status = raw.get("status")
    if status == "completed":
        return UndoDryRunPlan(
            undo_plan_id=undo_plan_id,
            manifest_path=str(store.undo_manifest_path(undo_plan_id)),
            library_id=str(raw.get("libraryId", "")),
            run_id=str(raw.get("runId", "")),
            total_count=0,
            recoverable_count=0,
            blocked_count=0,
            manual_required_count=0,
            items=(),
        )

    try:
        return plan_move_undo_from_store(
            library_root=library_root,
            store=store,
            undo_plan_id=undo_plan_id,
        )
    except UndoManifestValidationError as exc:
        raise _map_validation_error(exc) from exc
