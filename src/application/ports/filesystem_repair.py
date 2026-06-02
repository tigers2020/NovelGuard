"""Port for in-place UTF-8 repair (PR-22)."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from application.ports.filesystem_apply import ApplyRowResult


class FilesystemRepairPort(Protocol):
    def read_bytes(self, path: Path) -> bytes: ...

    def backup_original(
        self,
        backup_dir: Path,
        *,
        original_bytes: bytes,
        metadata: dict[str, object],
    ) -> ApplyRowResult: ...

    def write_utf8_atomic(
        self,
        path: Path,
        text: str,
        *,
        temp_suffix: str,
    ) -> ApplyRowResult: ...
