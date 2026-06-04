"""Duplicate archive outside the library root (not rescanned with the library)."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

# Legacy in-library output dirs — excluded from library scans.
LIBRARY_OUTPUT_DIR_NAMES = frozenset({"duplicate", "organized"})

# UI / review row label (logical target, not a library-relative path).
DUPLICATE_TARGET_FOLDER_LABEL = "duplicate/"


def duplicate_archive_root(library_root: Path) -> Path:
    """Sibling folder: ``{parent}/{library_name}_duplicate``."""
    resolved = library_root.resolve()
    name = resolved.name or "library"
    return resolved.parent / f"{name}_duplicate"


def is_path_under_duplicate_archive(path: Path, library_root: Path) -> bool:
    archive = duplicate_archive_root(library_root).resolve()
    try:
        path.resolve().relative_to(archive)
        return True
    except ValueError:
        return False


def build_duplicate_archive_dest(library_root: Path, source_basename: str) -> Path:
    return duplicate_archive_root(library_root) / source_basename


def allocate_unique_dest_path(
    dest: Path,
    *,
    path_exists: Callable[[Path], bool],
) -> Path:
    """Return ``dest`` or ``stem (n).ext`` when the path already exists."""
    if not path_exists(dest):
        return dest
    parent = dest.parent
    stem = dest.stem
    suffix = dest.suffix
    for index in range(2, 10_000):
        candidate = parent / f"{stem} ({index}){suffix}"
        if not path_exists(candidate):
            return candidate
    return dest
