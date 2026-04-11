"""폴더 스캔 직후 결과 (UseCase 이전 단계)."""

from dataclasses import dataclass

from domain.entities.file_entry import FileEntry


@dataclass(frozen=True)
class FolderScanOutcome:
    """스캐너가 반환하는 스캔 결과.

    경고는 스캔은 계속했지만 일부 항목을 건너뛴 경우(권한·I/O 등)를 센다.
    """

    entries: list[FileEntry]
    warnings_count: int
