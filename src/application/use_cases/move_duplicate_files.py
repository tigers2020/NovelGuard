"""중복 파일 이동 UseCase."""
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from application.ports.log_sink import ILogSink
from application.utils.debug_logger import debug_step

if TYPE_CHECKING:
    from gui.models.file_data_store import FileDataStore


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
        self,
        file_data_store: "FileDataStore",
        log_sink: Optional[ILogSink] = None
    ) -> None:
        """UseCase 초기화.
        
        Args:
            file_data_store: 파일 데이터 저장소.
            log_sink: 로그 싱크 (선택적).
        """
        self._file_data_store = file_data_store
        self._log_sink = log_sink
    
    def execute(
        self,
        scan_folder: Path,
        dry_run: bool = True
    ) -> list[MoveOperation]:
        """중복 파일 이동 작업 목록 생성.
        
        Args:
            scan_folder: 스캔 폴더 경로.
            dry_run: True면 실제 이동하지 않고 작업 목록만 반환.
        
        Returns:
            이동 작업 목록 (MoveOperation 리스트).
        """
        debug_step(
            self._log_sink,
            "move_duplicate_files_start",
            {
                "scan_folder": str(scan_folder),
                "dry_run": dry_run
            }
        )
        
        # 모든 파일 조회
        all_files = self._file_data_store.get_all_files()
        
        # 이동 대상 파일 필터링
        move_operations: list[MoveOperation] = []
        
        for file_data in all_files:
            # 대표 파일은 유지 (이동하지 않음)
            # - duplicate_group_id is None: 그룹 없는 개인 (자체가 대표)
            # - is_canonical is True: 그룹 내 대표 파일
            if file_data.duplicate_group_id is None:
                continue  # 그룹 없는 개인은 대표
        
            if file_data.is_canonical:
                continue  # 대표 파일은 유지
            
            # 중복 파일은 이동 대상
            source_path = file_data.path
            try:
                relative_path = source_path.relative_to(scan_folder)
            except ValueError:
                # scan_folder와 관계없는 경로인 경우 (드물게 발생)
                # 절대 경로 사용
                relative_path = Path(source_path.name)
            target_path = scan_folder / "duplicate" / relative_path
            
            move_operations.append(MoveOperation(
                source_path=source_path,
                target_path=target_path,
                file_id=file_data.file_id,
                duplicate_group_id=file_data.duplicate_group_id
            ))
        
        debug_step(
            self._log_sink,
            "move_duplicate_files_completed",
            {
                "total_files": len(all_files),
                "move_operations_count": len(move_operations),
                "dry_run": dry_run
            }
        )
        
        return move_operations
