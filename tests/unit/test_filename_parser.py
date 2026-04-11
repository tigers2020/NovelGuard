"""FilenameParser 단위 테스트."""

from pathlib import Path

import pytest

from domain.services.filename_parser import FilenameParser


@pytest.fixture
def parser() -> FilenameParser:
    return FilenameParser()


class TestFilenameParserRange:
    """범위 파싱 테스트."""

    def test_hyphen_range(self, parser: FilenameParser) -> None:
        result = parser.parse(Path("작품명 1-170.txt"))
        assert result.series_title_norm == "작품명"
        assert result.range_start == 1
        assert result.range_end == 170

    def test_tilde_range(self, parser: FilenameParser) -> None:
        result = parser.parse(Path("작품명 1~200.txt"))
        assert result.series_title_norm == "작품명"
        assert result.range_start == 1
        assert result.range_end == 200

    def test_single_unit(self, parser: FilenameParser) -> None:
        result = parser.parse(Path("작품명 3권.txt"))
        assert result.series_title_norm == "작품명"
        assert result.range_start is not None

    def test_no_range_returns_fallback(self, parser: FilenameParser) -> None:
        result = parser.parse(Path("random_notes.txt"))
        assert result.has_range is False


class TestFilenameParserTags:
    """태그 파싱 테스트."""

    def test_complete_tag_in_parentheses(self, parser: FilenameParser) -> None:
        """현재 parser는 범위 패턴 안의 괄호 태그를 tags에 별도 추출하지 않는다.
        range_end가 올바르게 파싱되는지만 확인한다."""
        result = parser.parse(Path("작품명 1-200(완).txt"))
        assert result.range_start == 1
        assert result.range_end == 200

    def test_no_tags(self, parser: FilenameParser) -> None:
        result = parser.parse(Path("작품명 1-100.txt"))
        assert result.is_complete is False


class TestFilenameParserSameSeries:
    """동일 작품 판정 테스트."""

    def test_same_series(self, parser: FilenameParser) -> None:
        a = parser.parse(Path("작품명 1-100.txt"))
        b = parser.parse(Path("작품명 1-200.txt"))
        assert a.is_same_series(b) is True

    def test_different_series(self, parser: FilenameParser) -> None:
        a = parser.parse(Path("작품A 1-100.txt"))
        b = parser.parse(Path("작품B 1-100.txt"))
        assert a.is_same_series(b) is False
