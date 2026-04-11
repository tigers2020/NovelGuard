"""KeeperScoreService 단위 테스트."""

from datetime import datetime
from pathlib import Path

import pytest

from domain.entities.file_entry import FileEntry
from domain.services.keeper_score_service import KeeperScoreService
from domain.value_objects.detection_config import DetectionDefaults
from domain.value_objects.filename_parse_result import FilenameParseResult


def _entry(file_id: int, size: int = 1000, mtime: datetime | None = None) -> FileEntry:
    return FileEntry(
        path=Path(f"file_{file_id}.txt"),
        size=size,
        mtime=mtime or datetime(2025, 1, 1),
        extension=".txt",
        file_id=file_id,
    )


def _parse(
    name: str = "작품",
    start: int = 1,
    end: int = 100,
    confidence: float = 0.9,
    tags: list[str] | None = None,
) -> FilenameParseResult:
    return FilenameParseResult(
        original_path=Path(f"{name}.txt"),
        original_name=name,
        series_title_norm=name,
        range_start=start,
        range_end=end,
        confidence=confidence,
        parse_method="pattern_match",
        tags=tags or [],
    )


@pytest.fixture
def service() -> KeeperScoreService:
    return KeeperScoreService()


class TestCalculateKeeperScore:
    def test_complete_tag_adds_score(self, service: KeeperScoreService) -> None:
        entry = _entry(1)
        parse = _parse(tags=["완"])
        score = service.calculate_keeper_score(entry, parse)
        assert score >= DetectionDefaults.SCORE_COMPLETE_TAG

    def test_low_confidence_penalised(self, service: KeeperScoreService) -> None:
        entry = _entry(1)
        parse = _parse(confidence=0.1)
        score = service.calculate_keeper_score(entry, parse)
        assert score < 0


class TestSelectKeeper:
    def test_complete_preferred(self, service: KeeperScoreService) -> None:
        complete = (_entry(1, size=500), _parse(tags=["완"]))
        partial = (_entry(2, size=1000), _parse())
        keeper = service.select_keeper([complete, partial])
        assert keeper is not None
        assert keeper.file_id == 1

    def test_single_file(self, service: KeeperScoreService) -> None:
        entry = _entry(1)
        keeper = service.select_keeper([(entry, _parse())])
        assert keeper is entry

    def test_empty_returns_none(self, service: KeeperScoreService) -> None:
        assert service.select_keeper([]) is None
