"""Composition root helpers for LibrarySession."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from app.apply_quality_repair import ApplyQualityRepairUseCase
from app.apply_resolved_actions import ApplyResolvedActionsUseCase
from app.bridge_api import BridgeApi
from app.build_preview_plan import BuildPreviewPlanUseCase
from app.build_quality_repair_plan import BuildQualityRepairPlanUseCase
from app.preview_apply_guard import PreviewApplyGuard
from app.quality_repair_guard import QualityRepairGuard
from application.audit_log import AuditLog
from application.finalize_runner import FinalizeRunner
from application.library_session import LibrarySession
from application.ports.filesystem_apply import FilesystemApplyPort
from application.ports.filesystem_repair import FilesystemRepairPort
from application.ports.library_index import LibraryIndexPort
from infrastructure.content_hasher import hash_file
from infrastructure.filesystem_scanner import scan_folder
from infrastructure.finalize_cleanup import LocalFinalizeCleanupAdapter
from infrastructure.local_filesystem_apply import LocalFilesystemApplyAdapter
from infrastructure.local_filesystem_repair import LocalFilesystemRepairAdapter
from infrastructure.sqlite_library_index import SqliteLibraryIndex


def default_library_db_path() -> Path:
    return Path.home() / ".novelguard" / "library.db"


def default_audit_log_path() -> Path:
    return Path.home() / ".novelguard" / "apply-audit.jsonl"


def default_repair_backup_root() -> Path:
    return Path.home() / ".novelguard" / "SAVE" / "repair_backup"


def default_finalize_save_root() -> Path:
    return Path.home() / ".novelguard" / "SAVE" / "finalize"


def _scan_with_content_hash(
    folder_path: str,
    *,
    on_progress: Callable[..., None],
    cancel_check: Callable[..., bool],
    out: Callable[..., None],
    extensions: set[str] | None = None,
    content_hash_fn: Callable[..., str] | None = None,
) -> None:
    _ = content_hash_fn
    scan_folder(
        folder_path,
        on_progress=on_progress,
        cancel_check=cancel_check,
        out=out,
        extensions=extensions,
        content_hash_fn=hash_file,
    )


def create_library_session(
    index: LibraryIndexPort | None = None,
    *,
    db_path: Path | None = None,
    audit_log_path: Path | None = None,
) -> LibrarySession:
    if index is None:
        path = db_path or default_library_db_path()
        index = SqliteLibraryIndex(path)
    session = LibrarySession(index, scan_folder=_scan_with_content_hash)
    audit_path = audit_log_path or default_audit_log_path()
    finalize_runner = FinalizeRunner(
        cleanup=LocalFinalizeCleanupAdapter(),
        save_root=default_finalize_save_root(),
        audit_log_path=audit_path,
    )
    session.configure_finalize(finalize_runner)
    return session


def create_bridge_api(
    session: LibrarySession | None = None,
    *,
    audit_log_path: Path | None = None,
    filesystem: FilesystemApplyPort | None = None,
    repair_filesystem: FilesystemRepairPort | None = None,
    repair_backup_root: Path | None = None,
) -> BridgeApi:
    """Composition root for pywebview BridgeApi + PR-15 apply + PR-22 repair."""
    resolved_session = session or create_library_session()
    move_guard = PreviewApplyGuard()
    repair_guard = QualityRepairGuard()
    audit = AuditLog(audit_log_path or default_audit_log_path())
    fs = filesystem or LocalFilesystemApplyAdapter()
    repair_fs = repair_filesystem or LocalFilesystemRepairAdapter()
    backup_root = repair_backup_root or default_repair_backup_root()
    preview_use_case = BuildPreviewPlanUseCase(
        resolved_session, move_guard, repair_guard, audit, fs
    )
    apply_use_case = ApplyResolvedActionsUseCase(resolved_session, move_guard, audit, fs)
    repair_preview_use_case = BuildQualityRepairPlanUseCase(
        resolved_session, move_guard, repair_guard, audit
    )
    repair_apply_use_case = ApplyQualityRepairUseCase(
        resolved_session,
        move_guard,
        repair_guard,
        audit,
        repair_fs,
        backup_root=backup_root,
    )
    return BridgeApi(
        resolved_session,
        guard=move_guard,
        repair_guard=repair_guard,
        preview_use_case=preview_use_case,
        apply_use_case=apply_use_case,
        repair_preview_use_case=repair_preview_use_case,
        repair_apply_use_case=repair_apply_use_case,
    )
