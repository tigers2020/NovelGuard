"""Composition root helpers for LibrarySession."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from app.apply_resolved_actions import ApplyResolvedActionsUseCase
from app.bridge_api import BridgeApi
from app.build_preview_plan import BuildPreviewPlanUseCase
from app.preview_apply_guard import PreviewApplyGuard
from application.audit_log import AuditLog
from application.library_session import LibrarySession
from application.ports.filesystem_apply import FilesystemApplyPort
from application.ports.library_index import LibraryIndexPort
from infrastructure.content_hasher import hash_file
from infrastructure.filesystem_scanner import scan_folder
from infrastructure.local_filesystem_apply import LocalFilesystemApplyAdapter
from infrastructure.sqlite_library_index import SqliteLibraryIndex


def default_library_db_path() -> Path:
    return Path.home() / ".novelguard" / "library.db"


def default_audit_log_path() -> Path:
    return Path.home() / ".novelguard" / "apply-audit.jsonl"


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
) -> LibrarySession:
    if index is None:
        path = db_path or default_library_db_path()
        index = SqliteLibraryIndex(path)
    return LibrarySession(index, scan_folder=_scan_with_content_hash)


def create_bridge_api(
    session: LibrarySession | None = None,
    *,
    audit_log_path: Path | None = None,
    filesystem: FilesystemApplyPort | None = None,
) -> BridgeApi:
    """Composition root for pywebview BridgeApi + PR-15 apply use cases."""
    resolved_session = session or create_library_session()
    guard = PreviewApplyGuard()
    audit = AuditLog(audit_log_path or default_audit_log_path())
    fs = filesystem or LocalFilesystemApplyAdapter()
    preview_use_case = BuildPreviewPlanUseCase(resolved_session, guard, audit, fs)
    apply_use_case = ApplyResolvedActionsUseCase(resolved_session, guard, audit, fs)
    return BridgeApi(
        resolved_session,
        guard=guard,
        preview_use_case=preview_use_case,
        apply_use_case=apply_use_case,
    )
