"""Filesystem file content reader."""

from pathlib import Path


class FileSystemContentReader:
    """Read bytes from the local filesystem."""

    def read_bytes(self, path: Path, max_bytes: int | None = None) -> bytes:
        data = path.read_bytes()
        if max_bytes is not None and len(data) > max_bytes:
            return data[:max_bytes]
        return data
