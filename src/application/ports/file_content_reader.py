"""File content reader port."""

from pathlib import Path
from typing import Protocol


class FileContentReader(Protocol):
    """Read raw bytes from a file path (infrastructure implements)."""

    def read_bytes(self, path: Path, max_bytes: int | None = None) -> bytes: ...
