"""Production and dev path resolution for NovelGuard desktop runtime."""

from __future__ import annotations

import hashlib
import os
import sys
from dataclasses import dataclass
from pathlib import Path

APP_NAME = "NovelGuard"

ENV_LOCALAPPDATA_OVERRIDE = "NOVELGUARD_LOCALAPPDATA"
ENV_APPDATA_OVERRIDE = "NOVELGUARD_APPDATA"
ENV_BUNDLE_ROOT_OVERRIDE = "NOVELGUARD_BUNDLE_ROOT"


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def _repo_root() -> Path:
    # src/app/runtime_paths.py -> src/app -> src -> repo
    return Path(__file__).resolve().parents[2]


def app_root() -> Path:
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return _repo_root()


def bundle_root() -> Path:
    override = os.environ.get(ENV_BUNDLE_ROOT_OVERRIDE)
    if override:
        return Path(override).expanduser().resolve()

    if is_frozen():
        # PyInstaller commonly exposes bundled datas through _MEIPASS.
        return Path(getattr(sys, "_MEIPASS", app_root())).resolve()

    return app_root()


def frontend_asset_root() -> Path:
    if is_frozen():
        return bundle_root() / "web" / "build"
    return app_root() / "web" / "build"


def _local_app_data_root() -> Path:
    override = os.environ.get(ENV_LOCALAPPDATA_OVERRIDE)
    if override:
        return Path(override).expanduser().resolve()

    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data).expanduser().resolve()

    # Dev / non-Windows fallback. Not the Windows packaged target.
    return Path.home() / ".local" / "share"


def _roaming_app_data_root() -> Path:
    override = os.environ.get(ENV_APPDATA_OVERRIDE)
    if override:
        return Path(override).expanduser().resolve()

    app_data = os.environ.get("APPDATA")
    if app_data:
        return Path(app_data).expanduser().resolve()

    # Dev / non-Windows fallback. Not the Windows packaged target.
    return Path.home() / ".config"


def user_data_dir() -> Path:
    return _local_app_data_root() / APP_NAME


def state_root() -> Path:
    return user_data_dir() / "state"


def logs_dir() -> Path:
    return user_data_dir() / "logs"


def config_dir() -> Path:
    return _roaming_app_data_root() / APP_NAME


def normalize_library_root(library_root: Path) -> Path:
    return library_root.expanduser().resolve()


def library_id_for_root(library_root: Path) -> str:
    normalized = str(normalize_library_root(library_root))

    # Windows paths are case-insensitive. This keeps IDs stable across casing.
    if os.name == "nt":
        normalized = normalized.casefold()

    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def library_state_dir(library_id: str) -> Path:
    if not library_id or any(part in library_id for part in ("/", "\\", "..")):
        raise ValueError("invalid library_id")
    return state_root() / "libraries" / library_id


def library_db_path(library_id: str) -> Path:
    return library_state_dir(library_id) / "library.db"


def apply_audit_path(library_id: str) -> Path:
    return library_state_dir(library_id) / "apply-audit.jsonl"


def recovery_checkpoints_path(library_id: str) -> Path:
    return library_state_dir(library_id) / "recovery-checkpoints.jsonl"


def undo_plans_dir(library_id: str) -> Path:
    return library_state_dir(library_id) / "undo-plans"


def save_dir_for_library(library_root: Path) -> Path:
    return normalize_library_root(library_root) / "SAVE"


def reports_dir_for_library(library_root: Path) -> Path:
    return save_dir_for_library(library_root) / "reports"


PENDING_LIBRARY_ID = "_pending"


@dataclass(frozen=True, slots=True)
class LibraryRuntimePaths:
    library_root: Path
    library_id: str
    db_path: Path
    audit_log_path: Path
    recovery_checkpoints_path: Path
    undo_plans_dir: Path
    finalize_save_root: Path
    repair_backup_root: Path


def library_runtime_paths(library_root: Path) -> LibraryRuntimePaths:
    root = normalize_library_root(library_root)
    library_id = library_id_for_root(root)
    save_root = save_dir_for_library(root)
    return LibraryRuntimePaths(
        library_root=root,
        library_id=library_id,
        db_path=library_db_path(library_id),
        audit_log_path=apply_audit_path(library_id),
        recovery_checkpoints_path=recovery_checkpoints_path(library_id),
        undo_plans_dir=undo_plans_dir(library_id),
        finalize_save_root=save_root / "finalize",
        repair_backup_root=save_root / "repair_backup",
    )


def pending_library_runtime_paths() -> LibraryRuntimePaths:
    """Placeholder paths before the user selects a library folder."""
    placeholder_root = state_root() / "_pending" / "library_root"
    save_root = save_dir_for_library(placeholder_root)
    return LibraryRuntimePaths(
        library_root=placeholder_root,
        library_id=PENDING_LIBRARY_ID,
        db_path=library_db_path(PENDING_LIBRARY_ID),
        audit_log_path=apply_audit_path(PENDING_LIBRARY_ID),
        recovery_checkpoints_path=recovery_checkpoints_path(PENDING_LIBRARY_ID),
        undo_plans_dir=undo_plans_dir(PENDING_LIBRARY_ID),
        finalize_save_root=save_root / "finalize",
        repair_backup_root=save_root / "repair_backup",
    )


def ensure_library_state_dirs(paths: LibraryRuntimePaths) -> None:
    paths.db_path.parent.mkdir(parents=True, exist_ok=True)
    paths.audit_log_path.parent.mkdir(parents=True, exist_ok=True)
    paths.undo_plans_dir.mkdir(parents=True, exist_ok=True)
