from __future__ import annotations

from domain.models import FileRecord
from domain.quality import QualityIssue


class MemoryLibraryIndex:
    def __init__(self) -> None:
        self._current_folder: str | None = None
        self._files: list[FileRecord] = []
        self._quality_issues: list[QualityIssue] = []

    def clear(self) -> None:
        self._current_folder = None
        self._files = []
        self._quality_issues = []

    def replace_files(self, folder_path: str, files: list[FileRecord]) -> None:
        self._current_folder = folder_path
        self._files = list(files)

    @property
    def folder_path(self) -> str | None:
        return self._current_folder

    def files(self) -> list[FileRecord]:
        if self._current_folder is None:
            return []
        return list(self._files)

    def file_count(self) -> int:
        return len(self._files)

    def total_bytes(self) -> int:
        return sum(f.size_bytes for f in self._files)

    def replace_quality_issues(self, folder_path: str, issues: list[QualityIssue]) -> None:
        self._current_folder = folder_path
        self._quality_issues = list(issues)

    def quality_issues(self) -> list[QualityIssue]:
        if self._current_folder is None:
            return []
        return list(self._quality_issues)
