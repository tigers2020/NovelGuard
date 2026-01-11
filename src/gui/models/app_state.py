"""전역 애플리케이션 상태 관리."""
from dataclasses import dataclass, field
from typing import Optional

from gui.models.file_data_store import FileDataStore


@dataclass
class AppState:
    """애플리케이션 전역 상태."""
    
    # 통계 정보
    total_files: int = 0
    processed_files: int = 0
    saved_size_gb: float = 0.0
    
    # 현재 선택된 탭
    current_tab: str = "scan"
    
    # 스캔 상태
    scan_folder: Optional[str] = None
    is_scanning: bool = False
    
    # 파일 데이터 저장소 (인스턴스는 별도로 생성)
    _file_data_store: Optional[FileDataStore] = field(default=None, init=False)
    
    def update_stats(self, total: int, processed: int, saved_gb: float) -> None:
        """통계 정보 업데이트."""
        self.total_files = total
        self.processed_files = processed
        self.saved_size_gb = saved_gb
    
    @property
    def file_data_store(self) -> FileDataStore:
        """파일 데이터 저장소 반환 (없으면 생성)."""
        if self._file_data_store is None:
            self._file_data_store = FileDataStore()
        return self._file_data_store
