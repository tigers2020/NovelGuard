"""MoveDuplicateFilesUseCase 단위 테스트."""

from datetime import datetime
from pathlib import Path

from application.dto.file_data import FileData
from application.use_cases.move_duplicate_files import MoveDuplicateFilesUseCase
from domain.entities.file_entry import FileEntry


class FakeFileDataStore:
    """IFileDataStore 프로토콜을 만족하는 Fake."""

    def __init__(self, files: list[FileData]) -> None:
        self._files = {f.file_id: f for f in files}

    def get_file(self, file_id: int):
        return self._files.get(file_id)

    def get_all_files(self) -> list[FileData]:
        return list(self._files.values())

    def get_file_id_by_path(self, path):
        for f in self._files.values():
            if f.path == path:
                return f.file_id
        return None

    def get_file_count(self) -> int:
        return len(self._files)


def _file_data(
    file_id: int,
    name: str,
    *,
    duplicate_group_id: int | None = None,
    is_canonical: bool = False,
) -> FileData:
    entry = FileEntry(
        path=Path(f"/scan/{name}"),
        size=1024,
        mtime=datetime(2025, 1, 1),
        extension=".txt",
        file_id=file_id,
    )
    return FileData(
        entry=entry,
        file_id=file_id,
        duplicate_group_id=duplicate_group_id,
        is_canonical=is_canonical,
    )


class TestExecute:
    def test_non_duplicate_files_not_moved(self) -> None:
        store = FakeFileDataStore([_file_data(1, "a.txt")])
        uc = MoveDuplicateFilesUseCase(store)
        ops = uc.execute(Path("/scan"))
        assert ops == []

    def test_canonical_kept(self) -> None:
        store = FakeFileDataStore(
            [
                _file_data(1, "a.txt", duplicate_group_id=1, is_canonical=True),
                _file_data(2, "b.txt", duplicate_group_id=1, is_canonical=False),
            ]
        )
        uc = MoveDuplicateFilesUseCase(store)
        ops = uc.execute(Path("/scan"))
        assert len(ops) == 1
        assert ops[0].file_id == 2
        assert ops[0].target_path.parent == Path("/scan/duplicate")

    def test_duplicate_name_collision_resolved(self) -> None:
        store = FakeFileDataStore(
            [
                _file_data(1, "keeper.txt", duplicate_group_id=1, is_canonical=True),
                _file_data(2, "dup.txt", duplicate_group_id=1),
                _file_data(3, "dup.txt", duplicate_group_id=2),
            ]
        )
        uc = MoveDuplicateFilesUseCase(store)
        ops = uc.execute(Path("/scan"))
        targets = [o.target_path.name for o in ops]
        assert len(set(targets)) == len(targets), "target names must be unique"
