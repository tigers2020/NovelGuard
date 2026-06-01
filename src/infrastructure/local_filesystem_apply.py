"""Local filesystem adapter for PR-15 move_duplicate apply."""

from __future__ import annotations

import shutil
from pathlib import Path

from application.ports.filesystem_apply import ApplyRowResult


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
            shutil.move(str(src), str(dest))
        except OSError as exc:
            return ApplyRowResult(outcome="error", error=str(exc))

        if not dest.is_file():
            return ApplyRowResult(outcome="error", error=f"move failed: {dest}")
        if src.exists():
            return ApplyRowResult(outcome="error", error=f"source still present after move: {src}")

        return ApplyRowResult(outcome="ok")
