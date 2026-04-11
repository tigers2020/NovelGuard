"""BlockingService 단위 테스트."""

from datetime import datetime
from pathlib import Path

import pytest

from domain.entities.file_entry import FileEntry
from domain.services.blocking_service import BlockingService
from domain.services.filename_parser import FilenameParser
from domain.value_objects.filename_parse_result import FilenameParseResult


def _entry(file_id: int, name: str = "file.txt") -> FileEntry:
    return FileEntry(
        path=Path(name),
        size=1024,
        mtime=datetime(2025, 1, 1),
        extension=".txt",
        file_id=file_id,
    )


def _parse(name: str, start: int, end: int, confidence: float = 0.9) -> FilenameParseResult:
    return FilenameParseResult(
        original_path=Path(f"{name} {start}-{end}.txt"),
        original_name=f"{name} {start}-{end}",
        series_title_norm=name,
        range_start=start,
        range_end=end,
        confidence=confidence,
        parse_method="pattern_match",
    )


@pytest.fixture
def service() -> BlockingService:
    return BlockingService(filename_parser=FilenameParser())


class TestCreateBlockingGroups:
    def test_same_range_start_grouped(self, service: BlockingService) -> None:
        """같은 series + 같은 range_start이면 하나의 BlockingGroup."""
        files = [
            (_entry(1, "작품 1-100.txt"), _parse("작품", 1, 100)),
            (_entry(2, "작품 1-200.txt"), _parse("작품", 1, 200)),
        ]
        groups = service.create_blocking_groups(files)
        assert len(groups) == 1
        assert set(groups[0].file_ids) == {1, 2}

    def test_different_series_separate(self, service: BlockingService) -> None:
        """다른 작품명이면 같은 range_start여도 별도 그룹."""
        files = [
            (_entry(1, "A 1-10.txt"), _parse("a", 1, 10)),
            (_entry(2, "A 1-20.txt"), _parse("a", 1, 20)),
            (_entry(3, "B 1-10.txt"), _parse("b", 1, 10)),
            (_entry(4, "B 1-20.txt"), _parse("b", 1, 20)),
        ]
        groups = service.create_blocking_groups(files)
        assert len(groups) == 2

    def test_single_file_no_group(self, service: BlockingService) -> None:
        """파일 1개뿐이면 BlockingGroup이 생성되지 않음."""
        files = [(_entry(1, "A 1-10.txt"), _parse("a", 1, 10))]
        groups = service.create_blocking_groups(files)
        assert groups == []

    def test_empty_input(self, service: BlockingService) -> None:
        assert service.create_blocking_groups([]) == []
