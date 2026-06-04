"""Local filesystem adapter for PR-15 move_duplicate apply."""

from __future__ import annotations

import errno
import os
import shutil
from pathlib import Path

from application.ports.filesystem_apply import ApplyRowResult


def _is_cross_device_error(exc: OSError) -> bool:
    if exc.errno == errno.EXDEV:
        return True
    # Windows: ERROR_NOT_SAME_DEVICE
    return getattr(exc, "winerror", None) == 17


def reliable_move(src: Path, dest: Path) -> None:
    """Move ``src`` to ``dest``; never leave both files without raising."""
    src_resolved = src.resolve()
    dest_resolved = dest.resolve()
    try:
        os.replace(src_resolved, dest_resolved)
        return
    except OSError as exc:
        if not _is_cross_device_error(exc):
            raise

    dest_resolved.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src_resolved, dest_resolved)
    try:
        src_resolved.unlink()
    except OSError as unlink_exc:
        if dest_resolved.exists():
            dest_resolved.unlink(missing_ok=True)
        raise OSError(f"failed to remove source after cross-volume move: {src_resolved}") from unlink_exc
    if src_resolved.exists():
        if dest_resolved.exists():
            dest_resolved.unlink(missing_ok=True)
        raise OSError(f"source still exists after cross-volume move: {src_resolved}")


class LocalFilesystemApplyAdapter:
    """Move-only adapter. Callers must validate paths via ApplyPathPolicy first."""

    def file_exists(self, path: Path) -> bool:
        return path.exists()

    def ensure_parent_dir(self, dest: Path) -> ApplyRowResult:
        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            return ApplyRowResult(outcome="error", error=str(exc))
        return ApplyRowResult(outcome="ok")

    def move_file(self, src: Path, dest: Path) -> ApplyRowResult:
        if not src.is_file():
            return ApplyRowResult(outcome="error", error=f"source not found: {src}")
        if dest.exists():
            return ApplyRowResult(outcome="error", error=f"destination exists: {dest}")

        parent_result = self.ensure_parent_dir(dest)
        if parent_result.outcome != "ok":
            return parent_result

        try:
            reliable_move(src, dest)
        except OSError as exc:
            return ApplyRowResult(outcome="error", error=str(exc))

        if not dest.is_file():
            return ApplyRowResult(outcome="error", error=f"move failed: {dest}")
        if src.exists():
            return ApplyRowResult(
                outcome="error",
                error=f"source still present after move: {src}",
            )

        return ApplyRowResult(outcome="ok")
