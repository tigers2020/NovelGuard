from __future__ import annotations

from typing import Protocol

from domain.models import FileRecord


class LibraryIndexPort(Protocol):
    def clear(self) -> None: ...

    def replace_files(self, folder_path: str, files: list[FileRecord]) -> None: ...

    @property
    def folder_path(self) -> str | None: ...

    def files(self) -> list[FileRecord]: ...

    def file_count(self) -> int: ...

    def total_bytes(self) -> int: ...
