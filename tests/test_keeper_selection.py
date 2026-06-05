"""Unit tests for canonical keeper selection (NOV-32)."""

from __future__ import annotations

from domain.keeper_selection import pick_keeper_file_id
from domain.models import FileRecord


def _file(file_id: str, size: int, mtime: int, path: str) -> FileRecord:
    return FileRecord(
        id=file_id,
        relative_path=path,
        name=path.split("/")[-1],
        size_bytes=size,
        modified_at_ns=mtime,
        content_sha256="a" * 64,
        extension=".txt",
    )


def test_keeper_picks_largest_size() -> None:
    files = [_file("a", 100, 1, "a.txt"), _file("b", 200, 1, "b.txt")]
    assert pick_keeper_file_id(files) == "b"


def test_keeper_picks_newest_when_size_tied() -> None:
    files = [_file("a", 100, 2, "a.txt"), _file("b", 100, 5, "b.txt")]
    assert pick_keeper_file_id(files) == "b"


def test_keeper_picks_lex_max_path_when_size_and_mtime_tied() -> None:
    files = [_file("a", 100, 1, "aaa.txt"), _file("b", 100, 1, "bbb.txt")]
    assert pick_keeper_file_id(files) == "b"
