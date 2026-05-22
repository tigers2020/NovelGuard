"""Real-world title variants → unified series_title_norm (blocking key)."""

from pathlib import Path

import pytest

from domain.services.filename_parser import FilenameParser


@pytest.fixture
def parser() -> FilenameParser:
    return FilenameParser()


class TestTitleVariantsSameNorm:
    def test_ampersand_vs_spaces_dungeon_commander(self, parser: FilenameParser) -> None:
        a = parser.parse(Path("던전 & 커맨더 1-2194.txt"))
        b = parser.parse(Path("던전  커맨더 1-2168.txt"))
        assert a.series_title_norm == b.series_title_norm
        assert a.is_same_series(b)
        assert a.range_start == 1 and b.range_start == 1
        assert a.range_end == 2194 and b.range_end == 2168

    def test_fullwidth_exclamation_and_author_tag(self, parser: FilenameParser) -> None:
        plain = parser.parse(Path("너네 스킬 다 내꺼 1-1308.txt"))
        variant = parser.parse(Path("너네 스킬 다 내꺼！ 1-1310@김단풍 (1).txt"))
        assert plain.series_title_norm == variant.series_title_norm
        assert plain.is_same_series(variant)
        assert plain.range_end == 1308
        assert variant.range_end == 1310

    def test_duplicate_plain_titles_identical_norm(self, parser: FilenameParser) -> None:
        a = parser.parse(Path("너네 스킬 다 내꺼 1-1308.txt"))
        b = parser.parse(Path("너네 스킬 다 내꺼 1-1308.txt"))
        assert a.series_title_norm == b.series_title_norm
