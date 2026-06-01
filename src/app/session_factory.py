"""Composition root helpers for LibrarySession."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from application.library_session import LibrarySession
from application.ports.library_index import LibraryIndexPort
from infrastructure.content_hasher import hash_file
from infrastructure.filesystem_scanner import scan_folder
from infrastructure.sqlite_library_index import SqliteLibraryIndex


def default_library_db_path() -> Path:
    return Path.home() / ".novelguard" / "library.db"


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
