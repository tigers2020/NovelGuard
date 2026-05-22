"""Exact duplicate detector — golden behavior and hash call counts."""

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from domain.entities.file_entry import FileEntry
from domain.ports.staged_content_fingerprints import StagedContentFingerprints
from domain.services.exact_duplicate_detector import ExactDuplicateDetector
from domain.value_objects.blocking_group import BlockingGroup
from domain.value_objects.detection_config import DetectionDefaults


@dataclass
class _CountingHashService:
    file_open_count: int = 0

    def read_staged_fingerprints(
        self,
        file_path: Path,
        file_size: int,
        *,
        need_full: bool = False,
    ) -> StagedContentFingerprints:
        self.file_open_count += 1
        pre = f"pre:{file_path.name}"
        suf = f"suf:{file_path.name}"
        full = f"full:{file_path.name}" if need_full else None
        return StagedContentFingerprints(prefix_hash=pre, suffix_hash=suf, full_hash=full)


def _staged_same_pre_suf(
    _path: Path, _file_size: int, *, need_full: bool = False
) -> StagedContentFingerprints:
    full = "same-full" if need_full else None
    return StagedContentFingerprints(prefix_hash="same-pre", suffix_hash="same-suf", full_hash=full)


def _entry(fid: int, name: str, size: int) -> FileEntry:
    return FileEntry(
        file_id=fid,
        path=Path(name),
        size=size,
        mtime=datetime(2020, 1, 1, tzinfo=timezone.utc),
        extension=".txt",
    )


def _groups(result) -> list[frozenset[int]]:
    return [frozenset(r.file_ids) for r in result.relations]


class TestExactGoldenBaseline:
    def test_two_large_identical_paths_same_size(self) -> None:
        hs = _CountingHashService()
        hs.read_staged_fingerprints = _staged_same_pre_suf  # type: ignore[method-assign]
        det = ExactDuplicateDetector(hs)
        entries = {1: _entry(1, "a.txt", 100_000), 2: _entry(2, "b.txt", 100_000)}
        bg = BlockingGroup(series_title_norm="", extension="", file_ids=[1, 2], range_start=None)
        result = det.detect_exact(bg, entries)
        assert _groups(result) == [frozenset({1, 2})]
        assert result.metrics.prefix_hash_count == 4
        assert result.metrics.suffix_hash_count == 4
        assert result.metrics.full_hash_count == 2
        assert result.metrics.file_open_count == 4

    def test_large_same_pre_suf_different_full_no_group(self) -> None:
        hs = _CountingHashService()

        def staged(path: Path, _fs: int, *, need_full: bool = False) -> StagedContentFingerprints:
            if need_full:
                full = "full-a" if path.name == "a.txt" else "full-b"
                return StagedContentFingerprints("same-pre", "same-suf", full)
            return StagedContentFingerprints("same-pre", "same-suf", None)

        hs.read_staged_fingerprints = staged  # type: ignore[method-assign]
        det = ExactDuplicateDetector(hs)
        entries = {1: _entry(1, "a.txt", 200_000), 2: _entry(2, "b.txt", 200_000)}
        bg = BlockingGroup(series_title_norm="", extension="", file_ids=[1, 2], range_start=None)
        result = det.detect_exact(bg, entries)
        assert result.relations == []


class TestExactPruningSmallFiles:
    """P2-1: size <= SAMPLE_SIZE → prefix hash covers full content; skip suffix/full."""

    def test_small_identical_prefix_only_one_group(self) -> None:
        hs = _CountingHashService()

        def staged(_path: Path, _fs: int, *, need_full: bool = False) -> StagedContentFingerprints:
            return StagedContentFingerprints("small-same", "small-same", None)

        hs.read_staged_fingerprints = staged  # type: ignore[method-assign]
        det = ExactDuplicateDetector(hs)
        s = DetectionDefaults.SAMPLE_SIZE
        entries = {1: _entry(1, "a.txt", s), 2: _entry(2, "b.txt", s)}
        bg = BlockingGroup(series_title_norm="", extension="", file_ids=[1, 2], range_start=None)
        result = det.detect_exact(bg, entries)
        assert _groups(result) == [frozenset({1, 2})]
        assert result.metrics.prefix_hash_count == 2
        assert result.metrics.suffix_hash_count == 2
        assert result.metrics.full_hash_count == 0
        assert result.metrics.file_open_count == 2
        rel = result.relations[0]
        assert rel.evidence["hash"] == "small-same"
        assert rel.evidence["prefix_hash"] == "small-same"
        assert rel.evidence["suffix_hash"] == "small-same"

    def test_small_different_prefix_no_group(self) -> None:
        hs = _CountingHashService()
        det = ExactDuplicateDetector(hs)
        entries = {1: _entry(1, "a.txt", 100), 2: _entry(2, "b.txt", 100)}
        bg = BlockingGroup(series_title_norm="", extension="", file_ids=[1, 2], range_start=None)
        result = det.detect_exact(bg, entries)
        assert result.relations == []
        assert result.metrics.full_hash_count == 0
        assert result.metrics.file_open_count == 2

    def test_large_same_pre_suf_still_requires_full_hash(self) -> None:
        """P2-2: size > SAMPLE must not skip full even when prefix+suffix match."""
        hs = _CountingHashService()

        def staged(path: Path, _fs: int, *, need_full: bool = False) -> StagedContentFingerprints:
            if need_full:
                full = "full-a" if path.name == "a.txt" else "full-b"
                return StagedContentFingerprints("same-pre", "same-suf", full)
            return StagedContentFingerprints("same-pre", "same-suf", None)

        hs.read_staged_fingerprints = staged  # type: ignore[method-assign]
        det = ExactDuplicateDetector(hs)
        entries = {1: _entry(1, "a.txt", 200_000), 2: _entry(2, "b.txt", 200_000)}
        bg = BlockingGroup(series_title_norm="", extension="", file_ids=[1, 2], range_start=None)
        result = det.detect_exact(bg, entries)
        assert result.relations == []
        assert result.metrics.full_hash_count == 2
