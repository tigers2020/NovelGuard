"""통계 및 리포트 탭 ViewModel."""
from typing import Optional

from PySide6.QtCore import QObject

from application.dto.ext_stat import ExtStat
from application.dto.run_summary import RunSummary
from application.ports.index_repository import IIndexRepository
from application.ports.log_sink import ILogSink
from application.utils.debug_logger import debug_step
from domain.entities.file_entry import FileEntry
from gui.view_models.base_view_model import BaseViewModel


class StatsViewModel(BaseViewModel):
    """통계 및 리포트 탭 ViewModel."""
    
    def __init__(
        self,
        parent: Optional[QObject] = None,
        index_repo: Optional[IIndexRepository] = None,
        log_sink: Optional[ILogSink] = None
    ) -> None:
        """통계 ViewModel 초기화.
        
        Args:
            parent: 부모 객체.
            index_repo: 인덱스 저장소 (선택적).
            log_sink: 로그 싱크 (선택적).
        """
        super().__init__(parent)
        
        self._index_repo = index_repo
        self._log_sink = log_sink
        
        # 통계 데이터
        self._latest_run_summary: Optional[RunSummary] = None
        self._ext_distribution: list[ExtStat] = []
        self._top_files: list[FileEntry] = []
    
    def load_data(self) -> None:
        """데이터 로드."""
        debug_step(self._log_sink, "stats_view_model_load_data_start")
        
        if not self._index_repo:
            debug_step(self._log_sink, "stats_view_model_load_data_no_repo")
            return
        
        try:
            # 최신 Run ID 조회
            latest_run_id = self._index_repo.get_latest_run_id()
            if latest_run_id is None:
                debug_step(self._log_sink, "stats_view_model_load_data_no_run_id")
                return
            
            debug_step(
                self._log_sink,
                "stats_view_model_load_data_run_id",
                {"latest_run_id": latest_run_id}
            )
            
            # Run 요약 조회
            self._latest_run_summary = self._index_repo.get_run_summary(latest_run_id)
            
            # 확장자별 분포 집계
            self._ext_distribution = self._index_repo.get_ext_distribution(latest_run_id)
            
            # 큰 파일 Top N (크기 내림차순)
            self._top_files = self._index_repo.list_files(
                latest_run_id,
                offset=0,
                limit=50,
                order_by="size_desc"
            )
            
            debug_step(
                self._log_sink,
                "stats_view_model_load_data_complete",
                {
                    "ext_distribution_count": len(self._ext_distribution),
                    "top_files_count": len(self._top_files),
                }
            )
            
            self.data_changed.emit()
        except Exception as e:
            # 에러는 로그에만 기록 (사용자에게는 빈 데이터 표시)
            debug_step(
                self._log_sink,
                "stats_view_model_load_data_error",
                {"error": str(e), "error_type": type(e).__name__}
            )
            self._latest_run_summary = None
            self._ext_distribution = []
            self._top_files = []
    
    @property
    def latest_run_summary(self) -> Optional[RunSummary]:
        """최신 Run 요약 반환."""
        return self._latest_run_summary
    
    @property
    def ext_distribution(self) -> list[ExtStat]:
        """확장자별 분포 반환."""
        return self._ext_distribution
    
    @property
    def top_files(self) -> list[FileEntry]:
        """큰 파일 Top N 반환."""
        return self._top_files
    
    def refresh(self) -> None:
        """데이터 새로고침."""
        self.load_data()
