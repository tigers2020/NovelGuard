"""FileEntry 도메인 엔티티 단위 테스트."""

from datetime import datetime
from pathlib import Path

import pytest

from domain.entities.file_entry import FileEntry


class TestFileEntry:
    """FileEntry 생성 및 유효성 검증."""

    def test_valid_creation(self) -> None:
        entry = FileEntry(
            path=Path("/tmp/test.txt"),
            size=1024,
            mtime=datetime(2025, 1, 1),
            extension=".txt",
        )
        assert entry.size == 1024
        assert entry.extension == ".txt"

    def test_negative_size_raises(self) -> None:
        with pytest.raises(ValueError, match="size must be >= 0"):
            FileEntry(
                path=Path("/tmp/test.txt"),
                size=-1,
                mtime=datetime(2025, 1, 1),
                extension=".txt",
            )

    def test_invalid_extension_raises(self) -> None:
        with pytest.raises(ValueError, match="extension must be empty or start with '.'"):
            FileEntry(
                path=Path("/tmp/test.txt"),
                size=100,
                mtime=datetime(2025, 1, 1),
                extension="txt",
            )

    def test_empty_extension_allowed(self) -> None:
        entry = FileEntry(
            path=Path("/tmp/noext"),
            size=0,
            mtime=datetime(2025, 1, 1),
            extension="",
        )
        assert entry.extension == ""

    def test_frozen(self) -> None:
        entry = FileEntry(
            path=Path("/tmp/test.txt"),
            size=100,
            mtime=datetime(2025, 1, 1),
            extension=".txt",
        )
        with pytest.raises(AttributeError):
            entry.size = 200  # type: ignore[misc]
