from __future__ import annotations

from domain.models import FileRecord


class MemoryLibraryIndex:
    def __init__(self) -> None:
        self._folder_path: str | None = None
        self._files: list[FileRecord] = []

    def clear(self) -> None:
        self._folder_path = None
        self._files = []

    def replace_files(self, folder_path: str, files: list[FileRecord]) -> None:
        self._folder_path = folder_path
        self._files = list(files)

    @property
    def folder_path(self) -> str | None:
        return self._folder_path

    def files(self) -> list[FileRecord]:
        return list(self._files)

    def file_count(self) -> int:
        return len(self._files)

    def total_bytes(self) -> int:
        return sum(f.size_bytes for f in self._files)
