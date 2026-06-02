"""Filesystem empty-directory cleanup under finalize allowlist (PR-23)."""

from __future__ import annotations

import os
from pathlib import Path

from application.ports.finalize_cleanup import CLEANUP_ALLOWED_ROOT_NAMES


class LocalFinalizeCleanupAdapter:
    def list_empty_dirs(self, library_root: str) -> list[str]:
        return _collect_empty_dirs(library_root)

    def remove_empty_dirs(self, library_root: str, relative_paths: list[str]) -> list[str]:
        root = Path(library_root).resolve()
        removed: list[str] = []
        for rel in relative_paths:
            target = _resolve_under_allowlist(root, rel)
            if target is None:
                continue
            if not target.is_dir():
                continue
            if any(target.iterdir()):
                continue
            target.rmdir()
            removed.append(rel.replace("\\", "/"))
        return removed


def _resolve_under_allowlist(root: Path, relative: str) -> Path | None:
    rel = Path(relative)
    if rel.is_absolute() or ".." in rel.parts:
        return None
    if not rel.parts or rel.parts[0] not in CLEANUP_ALLOWED_ROOT_NAMES:
        return None
    candidate = (root / rel).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return None
    return candidate


def _collect_empty_dirs(library_root: str) -> list[str]:
    root = Path(library_root).resolve()
    if not root.is_dir():
        return []
    candidates: list[Path] = []
    for name in CLEANUP_ALLOWED_ROOT_NAMES:
        base = root / name
        if base.is_dir():
            candidates.append(base)
    empty_rel: list[str] = []
    for base in candidates:
        for dirpath, dirnames, filenames in os.walk(base, topdown=False):
            path = Path(dirpath)
            if filenames or dirnames:
                continue
            rel = path.relative_to(root).as_posix()
            empty_rel.append(rel)
    return sorted(empty_rel)
