"""Rules for persisting the last library folder path across sessions."""

from __future__ import annotations

import os
from pathlib import Path

_ALLOW_EPHEMERAL_ENV = "NOVELGUARD_ALLOW_EPHEMERAL_LIBRARY"


def is_persistable_library_folder(folder: str) -> bool:
    """Return False for pytest basetemp paths that must not become the user default."""
    if os.environ.get(_ALLOW_EPHEMERAL_ENV) == "1":
        return True
    normalized = folder.replace("\\", "/").casefold()
    return "pytest-of-" not in normalized


def normalize_library_folder_path(folder: str) -> str:
    """Canonical folder key for SQLite (forward slashes, resolved)."""
    return Path(folder).expanduser().resolve().as_posix()
