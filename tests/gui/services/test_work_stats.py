"""Tests for gui.services.work_stats."""

from datetime import datetime
from pathlib import Path

from application.dto.file_data import FileData
from domain.entities.file_entry import FileEntry
from gui.models.file_data_store import FileDataStore
from gui.services.work_stats import compute_work_stats


def _file_data(
    file_id: int,
    name: str,
    *,
    size: int = 1024,
    duplicate_group_id: int | None = None,
    is_canonical: bool = False,
    integrity_severity: str | None = None,
) -> FileData:
    entry = FileEntry(
        path=Path(f"/scan/{name}"),
        size=size,
        mtime=datetime(2025, 1, 1),
        extension=".txt",
        file_id=file_id,
    )
    return FileData(
        entry=entry,
        file_id=file_id,
        duplicate_group_id=duplicate_group_id,
        is_canonical=is_canonical,
        integrity_severity=integrity_severity,
    )


def test_compute_work_stats_empty_store() -> None:
    store = FileDataStore()
    stats = compute_work_stats(store)
    assert stats.total_files == 0
    assert stats.duplicate_groups == 0
    assert stats.saved_gb == 0.0
    assert stats.integrity_issues == 0


def test_compute_work_stats_counts_duplicate_groups() -> None:
    store = FileDataStore()
    fd1 = _file_data(1, "a.txt", duplicate_group_id=1, is_canonical=True)
    fd2 = _file_data(2, "b.txt", size=2048, duplicate_group_id=1, is_canonical=False)
    store.add_file(fd1.entry)
    store.add_file(fd2.entry)
    store.set_duplicate_groups_batch(
        [
            (1, 1, True, None),
            (2, 1, False, None),
        ]
    )
    stats = compute_work_stats(store)
    assert stats.total_files == 2
    assert stats.duplicate_groups == 1
    assert stats.saved_gb > 0
    assert stats.duplicate_files == 1
