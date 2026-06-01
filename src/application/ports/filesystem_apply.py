"""Port for validated filesystem moves (PR-15 — move only, no delete)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Protocol

ApplyRowOutcome = Literal["ok", "error"]


@dataclass(frozen=True, slots=True)
class ApplyRowResult:
    outcome: ApplyRowOutcome
    error: str | None = None


class FilesystemApplyPort(Protocol):
    """Move-only filesystem operations. No delete/unlink APIs in PR-15."""

    def file_exists(self, path: Path) -> bool: ...

    def ensure_parent_dir(self, dest: Path) -> ApplyRowResult: ...

    def move_file(self, src: Path, dest: Path) -> ApplyRowResult: ...
