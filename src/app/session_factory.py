"""Composition root helpers for LibrarySession."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from app.apply_quality_repair import ApplyQualityRepairUseCase
from app.apply_resolved_actions import ApplyResolvedActionsUseCase
from app.bridge_api import BridgeApi
from app.build_preview_plan import BuildPreviewPlanUseCase
from app.build_quality_repair_plan import BuildQualityRepairPlanUseCase
from app.move_preview_facade import MovePreviewFacade
from app.preview_apply_guard import PreviewApplyGuard
from app.quality_repair_facade import QualityRepairFacade
from app.quality_repair_guard import QualityRepairGuard
from app.recovery_undo_facade import RecoveryUndoFacade
from app.runtime_paths import (
    LibraryRuntimePaths,
    config_dir,
    ensure_library_state_dirs,
    library_runtime_paths,
    pending_library_runtime_paths,
)
from app.undo_preview_guard import UndoPreviewGuard
from application.app_settings import AppSettings
from application.audit_log import AuditLog
from application.library_session import LibrarySession
from application.log_buffer import attach_session_log_handler
from application.ports.filesystem_apply import FilesystemApplyPort
from application.ports.filesystem_repair import FilesystemRepairPort
from application.ports.library_index import LibraryIndexPort
from application.recovery_store import JsonlRecoveryStore
from application.settings_store import SettingsStore
from infrastructure.filesystem_scanner import ScanStreamResult, scan_folder_stream
from infrastructure.local_filesystem_apply import LocalFilesystemApplyAdapter
from infrastructure.local_filesystem_repair import LocalFilesystemRepairAdapter
from infrastructure.memory_library_index import MemoryLibraryIndex
from infrastructure.sqlite_library_index import SqliteLibraryIndex


class SessionAuditLog(AuditLog):
    """Audit log whose path follows the active library binding on LibrarySession."""

    def __init__(self, session: LibrarySession) -> None:
        super().__init__(session.audit_log_path())
        self._session = session

    def append(self, event: str, **fields: object) -> None:
        self._path = self._session.audit_log_path()
        super().append(event, **fields)


class SessionRecoveryStore(JsonlRecoveryStore):
    """Recovery store whose paths follow the active library binding on LibrarySession."""

    def __init__(self, session: LibrarySession) -> None:
        super().__init__(
            checkpoints_path=session.recovery_checkpoints_path(),
            undo_plans_dir=session.undo_plans_dir(),
        )
        self._session = session

    def _refresh_paths(self) -> None:
        self._checkpoints_path = self._session.recovery_checkpoints_path()
        self._undo_plans_dir = self._session.undo_plans_dir()

    def append_checkpoint(self, record: dict[str, object]) -> None:
        self._refresh_paths()
        super().append_checkpoint(record)

    def write_undo_manifest(self, manifest: dict[str, object]) -> Path:
        self._refresh_paths()
        return super().write_undo_manifest(manifest)

    def list_undo_manifest_files(self) -> list[Path]:
        self._refresh_paths()
        return super().list_undo_manifest_files()


def _scan_with_content_probe(
    folder_path: str,
    *,
    on_progress: Callable[..., None],
    cancel_check: Callable[..., bool],
    out: Callable[..., None],
    extensions: set[str] | None = None,
    include_hidden: bool = False,
    content_hash_fn: Callable[..., str] | None = None,
    on_paths_collected: Callable[[int], None] | None = None,
) -> ScanStreamResult:
    _ = content_hash_fn
    return scan_folder_stream(
        folder_path,
        on_progress=on_progress,
        cancel_check=cancel_check,
        on_record=out,
        extensions=extensions,
        include_hidden=include_hidden,
        on_paths_collected=on_paths_collected,
    )


def bind_library_runtime(session: LibrarySession, folder: str) -> LibraryRuntimePaths:
    paths = library_runtime_paths(Path(folder))
    ensure_library_state_dirs(paths)
    session.apply_library_runtime(
        paths, rebind_sqlite=not isinstance(session.index, MemoryLibraryIndex)
    )
    return paths


def _create_app_settings() -> AppSettings:
    settings_dir = config_dir()
    settings_dir.mkdir(parents=True, exist_ok=True)
    store = SettingsStore(settings_dir / "settings.json")
    return AppSettings(store)


def create_library_session(
    index: LibraryIndexPort | None = None,
    *,
    db_path: Path | None = None,
    audit_log_path: Path | None = None,
    settings: AppSettings | None = None,
) -> LibrarySession:
    pending = pending_library_runtime_paths()
    ensure_library_state_dirs(pending)

    if index is None:
        path = db_path or pending.db_path
        path.parent.mkdir(parents=True, exist_ok=True)
        index = SqliteLibraryIndex(path)

    session = LibrarySession(
        index,
        scan_folder=_scan_with_content_probe,
        on_library_selected=bind_library_runtime,
        settings=settings or _create_app_settings(),
    )
    paths = pending
    if audit_log_path is not None:
        paths = LibraryRuntimePaths(
            library_root=pending.library_root,
            library_id=pending.library_id,
            db_path=db_path or pending.db_path,
            audit_log_path=audit_log_path,
            recovery_checkpoints_path=pending.recovery_checkpoints_path,
            undo_plans_dir=pending.undo_plans_dir,
            finalize_save_root=pending.finalize_save_root,
            repair_backup_root=pending.repair_backup_root,
        )
    session.apply_library_runtime(paths, rebind_sqlite=False)
    session.restore_last_library_folder()
    return session


def create_bridge_api(
    session: LibrarySession | None = None,
    *,
    audit_log_path: Path | None = None,
    filesystem: FilesystemApplyPort | None = None,
    repair_filesystem: FilesystemRepairPort | None = None,
    repair_backup_root: Path | None = None,
    recovery_store: SessionRecoveryStore | None = None,
    undo_preview_guard: UndoPreviewGuard | None = None,
) -> BridgeApi:
    """Composition root for pywebview BridgeApi + PR-15 apply + PR-22 repair."""
    resolved_session = session or create_library_session()
    move_guard = PreviewApplyGuard()
    repair_guard = QualityRepairGuard()

    if audit_log_path is not None:
        audit: AuditLog = AuditLog(audit_log_path)
    else:
        audit = SessionAuditLog(resolved_session)

    fs = filesystem or LocalFilesystemApplyAdapter()
    repair_fs = repair_filesystem or LocalFilesystemRepairAdapter()
    _ = repair_backup_root  # explicit override reserved for tests; repair reads session path

    preview_use_case = BuildPreviewPlanUseCase(
        resolved_session, move_guard, repair_guard, audit, fs
    )
    resolved_recovery_store = recovery_store or SessionRecoveryStore(resolved_session)
    undo_guard = undo_preview_guard or UndoPreviewGuard()
    apply_use_case = ApplyResolvedActionsUseCase(
        resolved_session, move_guard, audit, fs, recovery_store=resolved_recovery_store
    )
    repair_preview_use_case = BuildQualityRepairPlanUseCase(
        resolved_session, move_guard, repair_guard, audit
    )
    repair_apply_use_case = ApplyQualityRepairUseCase(
        resolved_session,
        move_guard,
        repair_guard,
        audit,
        repair_fs,
    )
    move_preview_facade = MovePreviewFacade(resolved_session, move_guard, apply_use_case)
    quality_repair_facade = QualityRepairFacade(
        resolved_session, repair_guard, repair_apply_use_case
    )
    recovery_undo_facade = RecoveryUndoFacade(
        resolved_session,
        resolved_recovery_store,
        undo_guard,
        filesystem=fs if isinstance(fs, LocalFilesystemApplyAdapter) else None,
    )
    attach_session_log_handler()
    return BridgeApi(
        resolved_session,
        guard=move_guard,
        repair_guard=repair_guard,
        preview_use_case=preview_use_case,
        apply_use_case=apply_use_case,
        repair_preview_use_case=repair_preview_use_case,
        repair_apply_use_case=repair_apply_use_case,
        move_preview_facade=move_preview_facade,
        quality_repair_facade=quality_repair_facade,
        recovery_undo_facade=recovery_undo_facade,
    )
