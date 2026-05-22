"""Updated anthology: same range_start, different range_end → VersionRelation."""

from datetime import datetime
from pathlib import Path

from domain.entities.file_entry import FileEntry
from domain.services.containment_detector import ContainmentDetector
from domain.services.filename_parser import FilenameParser


def _file(file_id: int, path: str, size: int = 10_000) -> FileEntry:
    return FileEntry(
        path=Path(path),
        size=size,
        mtime=datetime(2025, 6, 1),
        extension=".txt",
        file_id=file_id,
    )


def test_version_dungeon_commander_newer_end() -> None:
    parser = FilenameParser()
    det = ContainmentDetector()
    a = _file(1, "던전 & 커맨더 1-2194.txt", size=20_000)
    b = _file(2, "던전  커맨더 1-2168.txt", size=18_000)
    pa = parser.parse(a.path)
    pb = parser.parse(b.path)
    rel = det.detect_version(a, pa, b, pb)
    assert rel is not None
    assert rel.newer_file_id == 1
    assert rel.older_file_id == 2
    assert pa.range_end == 2194
    assert pb.range_end == 2168


def test_version_skill_title_fullwidth_punctuation() -> None:
    parser = FilenameParser()
    det = ContainmentDetector()
    older = _file(1, "너네 스킬 다 내꺼 1-1308.txt", size=9_000)
    newer = _file(2, "너네 스킬 다 내꺼！ 1-1310@김단풍 (1).txt", size=9_500)
    p_old = parser.parse(older.path)
    p_new = parser.parse(newer.path)
    rel = det.detect_version(older, p_old, newer, p_new)
    assert rel is not None
    assert rel.newer_file_id == 2
    assert rel.older_file_id == 1
