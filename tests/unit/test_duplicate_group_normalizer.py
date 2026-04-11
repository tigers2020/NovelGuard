"""duplicate_group_normalizer 단위 테스트."""

from datetime import datetime
from pathlib import Path
from typing import Optional, Union

from application.dto.duplicate_group_result import DuplicateGroupResult
from application.dto.file_data import FileData
from application.utils.duplicate_group_normalizer import (
    normalize_duplicate_groups,
    validate_normalized_groups,
)
from domain.entities.file_entry import FileEntry


class _FakeFileDataStore:
    """IFileDataStore 프로토콜을 만족하는 테스트용 fake."""

    def __init__(self, files: dict[int, FileData]) -> None:
        self._files = files

    def get_file(self, file_id: int) -> Optional[FileData]:
        return self._files.get(file_id)

    def get_all_files(self) -> list[FileData]:
        return list(self._files.values())

    def get_file_id_by_path(self, path: Union[str, Path]) -> Optional[int]:
        path_str = str(path)
        for fid, fd in self._files.items():
            if str(fd.path) == path_str:
                return fid
        return None

    def get_file_count(self) -> int:
        return len(self._files)


def _make_file_data(file_id: int, name: str, size: int = 100) -> FileData:
    return FileData(
        entry=FileEntry(
            path=Path(f"/tmp/{name}"),
            size=size,
            mtime=datetime(2025, 1, 1),
            extension=".txt",
        ),
        file_id=file_id,
    )


def _make_group(
    group_id: int,
    file_ids: list[int],
    dup_type: str = "containment",
    keeper: Optional[int] = None,
) -> DuplicateGroupResult:
    return DuplicateGroupResult(
        group_id=group_id,
        duplicate_type=dup_type,
        file_ids=file_ids,
        recommended_keeper_id=keeper,
        evidence={},
        confidence=0.9,
    )


class TestNormalizeDuplicateGroups:
    """Union-Find 병합 테스트."""

    def test_empty_groups(self) -> None:
        assert normalize_duplicate_groups([]) == []

    def test_single_group_no_merge(self) -> None:
        fd1 = _make_file_data(1, "a.txt")
        fd2 = _make_file_data(2, "b.txt")
        store = _FakeFileDataStore({1: fd1, 2: fd2})

        groups = [_make_group(1, [1, 2], keeper=1)]
        result = normalize_duplicate_groups(groups, store)
        assert len(result) == 1
        assert set(result[0].file_ids) == {1, 2}

    def test_overlapping_groups_merged(self) -> None:
        fds = {i: _make_file_data(i, f"{i}.txt") for i in range(1, 4)}
        store = _FakeFileDataStore(fds)

        groups = [
            _make_group(1, [1, 2], keeper=1),
            _make_group(2, [2, 3], keeper=2),
        ]
        result = normalize_duplicate_groups(groups, store)
        assert len(result) == 1
        assert set(result[0].file_ids) == {1, 2, 3}


class TestValidateNormalizedGroups:
    """정규화 후 검증 테스트."""

    def test_no_errors_for_valid(self) -> None:
        groups = [_make_group(1, [1, 2], keeper=1)]
        errors = validate_normalized_groups(groups)
        assert errors == []

    def test_duplicate_file_ids_detected(self) -> None:
        groups = [_make_group(1, [1, 1], keeper=1)]
        errors = validate_normalized_groups(groups)
        assert any("duplicate file_ids" in e for e in errors)
