"""Production and dev path resolution for NovelGuard desktop runtime."""

from __future__ import annotations

import hashlib
import os
import sys
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


def save_dir_for_library(library_root: Path) -> Path:
    return normalize_library_root(library_root) / "SAVE"


def reports_dir_for_library(library_root: Path) -> Path:
    return save_dir_for_library(library_root) / "reports"
