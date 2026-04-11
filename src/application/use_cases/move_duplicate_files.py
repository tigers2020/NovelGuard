"""중복 파일 이동 UseCase."""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from application.ports.file_data_store import IFileDataStore
from application.ports.log_sink import ILogSink
from application.utils.debug_logger import debug_step


@dataclass
class MoveOperation:
    """파일 이동 작업."""

    source_path: Path
    """원본 파일 경로."""

    target_path: Path
    """대상 파일 경로."""

    file_id: int
    """파일 ID."""

    duplicate_group_id: Optional[int] = None
    """중복 그룹 ID (있는 경우)."""


class MoveDuplicateFilesUseCase:
    """중복 파일 이동 UseCase.

    대표 파일을 제외한 중복 파일들을 duplicate/ 폴더로 이동합니다.
    """

    def __init__(
        self, file_data_store: IFileDataStore, log_sink: Optional[ILogSink] = None
    ) -> None:
        """UseCase 초기화.

        Args:
            file_data_store: 파일 데이터 저장소.
            log_sink: 로그 싱크 (선택적).
        """
        self._file_data_store = file_data_store
        self._log_sink = log_sink

    def execute(self, scan_folder: Path) -> list[MoveOperation]:
        """중복 파일 이동 계획(작업 목록)을 생성한다.

        실제 파일 이동은 수행하지 않는다.
        반환된 MoveOperation 리스트를 FileMoveWorker 등에서 실행한다.

        Args:
            scan_folder: 스캔 폴더 경로.

        Returns:
            이동 작업 목록 (MoveOperation 리스트).
        """
        debug_step(
            self._log_sink,
            "move_duplicate_files_start",
            {"scan_folder": str(scan_folder)},
        )

        # 모든 파일 조회
        all_files = self._file_data_store.get_all_files()

        # 이동 대상 파일 필터링. 서브폴더 무시하고 root/duplicate 안에만 평평하게 넣음.
        duplicate_dir = scan_folder / "duplicate"
        used_target_paths: set[Path] = set()
        move_operations: list[MoveOperation] = []

        for file_data in all_files:
            # 대표 파일은 유지 (이동하지 않음)
            # - duplicate_group_id is None: 그룹 없는 개인 (자체가 대표)
            # - is_canonical is True: 그룹 내 대표 파일
            if file_data.duplicate_group_id is None:
                continue  # 그룹 없는 개인은 대표

            if file_data.is_canonical:
                continue  # 대표 파일은 유지

            # 중복 파일은 이동 대상 → duplicate/ 아래에 파일명만 사용 (평평하게)
            source_path = file_data.path
            name = source_path.name
            stem, suffix = (source_path.stem, source_path.suffix)
            if suffix:
                suffix = "." + suffix
            target_path = duplicate_dir / name
            if target_path in used_target_paths:
                n = 1
                candidate = duplicate_dir / f"{stem} ({n}){suffix}"
                while candidate in used_target_paths:
                    n += 1
                    candidate = duplicate_dir / f"{stem} ({n}){suffix}"
                target_path = candidate
            used_target_paths.add(target_path)

            move_operations.append(
                MoveOperation(
                    source_path=source_path,
                    target_path=target_path,
                    file_id=file_data.file_id,
                    duplicate_group_id=file_data.duplicate_group_id,
                )
            )

        debug_step(
            self._log_sink,
            "move_duplicate_files_completed",
            {"total_files": len(all_files), "move_operations_count": len(move_operations)},
        )

        return move_operations
