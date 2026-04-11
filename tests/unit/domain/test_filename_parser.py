"""FilenameParser 단위 테스트."""

from pathlib import Path

import pytest

from domain.services.filename_parser import FilenameParser


@pytest.fixture
def parser() -> FilenameParser:
    return FilenameParser()


class TestBasicParsing:
    """기본 파일명 파싱 테스트."""

    def test_range_hyphen(self, parser: FilenameParser) -> None:
        result = parser.parse(Path("작품명 1-170.txt"))
        assert result.series_title_norm == "작품명"
        assert result.range_start == 1
        assert result.range_end == 170
        assert result.confidence > 0.0

    def test_range_tilde(self, parser: FilenameParser) -> None:
        result = parser.parse(Path("작품명 1~200.txt"))
        assert result.series_title_norm == "작품명"
        assert result.range_start == 1
        assert result.range_end == 200

    def test_single_range_with_unit(self, parser: FilenameParser) -> None:
        result = parser.parse(Path("작품명 5권.txt"))
        assert result.series_title_norm == "작품명"
        assert result.range_start == 5
        assert result.range_end == 5
        assert result.range_unit == "권"

    def test_no_range_fallback(self, parser: FilenameParser) -> None:
        result = parser.parse(Path("그냥파일.txt"))
        assert result.series_title_norm != ""
        assert result.parse_method == "fallback"

    def test_complete_tag_detected(self, parser: FilenameParser) -> None:
        result = parser.parse(Path("작품명 1-100(완결).txt"))
        assert result.is_complete is True

    def test_no_complete_tag(self, parser: FilenameParser) -> None:
        result = parser.parse(Path("작품명 1-100.txt"))
        assert result.is_complete is False


class TestEdgeCases:
    """경계 케이스."""

    def test_empty_stem(self, parser: FilenameParser) -> None:
        result = parser.parse(Path(".txt"))
        assert result.original_path == Path(".txt")

    def test_long_range(self, parser: FilenameParser) -> None:
        result = parser.parse(Path("대하소설 1-1445.txt"))
        assert result.range_start == 1
        assert result.range_end == 1445
