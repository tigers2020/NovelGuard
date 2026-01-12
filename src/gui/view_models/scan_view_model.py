"""스캔 탭 ViewModel."""
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, Signal

from application.dto.job_types import JobProgress, JobType
from application.dto.scan_result import ScanResult
from application.ports.job_runner import IJobRunner
from application.ports.log_sink import ILogSink
from application.utils.debug_logger import debug_step
from application.utils.extensions import parse_extensions
from gui.view_models.base_view_model import BaseViewModel


class ScanViewModel(BaseViewModel):
    """스캔 탭 ViewModel."""
    
    # 신규 시그널 추가
    scan_completed = Signal(ScanResult)  # 스캔 완료 시그널
    scan_error = Signal(str)  # 스캔 오류 시그널
    
    def __init__(
        self,
        parent: Optional[QObject] = None,
        job_manager: Optional[IJobRunner] = None,
        log_sink: Optional[ILogSink] = None
    ) -> None:
        """스캔 ViewModel 초기화.
        
        Args:
            parent: 부모 객체.
            job_manager: Job 관리자 (선택적).
            log_sink: 로그 싱크 (선택적).
        """
        super().__init__(parent)
        
        # 의존성 저장
        self._job_manager = job_manager
        self._log_sink = log_sink
        
        # 상태
        self._scan_folder: Optional[Path] = None
        self._is_scanning: bool = False
        self._progress_count: int = 0
        self._progress_message: str = ""
        
        # 설정
        self._extension_filter: str = ""
        self._include_subdirs: bool = True
        self._incremental_scan: bool = True
        self._include_hidden: bool = False
        self._include_symlinks: bool = True
        
        # Job ID
        self._current_job_id: Optional[int] = None
        
        # JobManager 시그널 연결 (QtJobManager인 경우)
        if job_manager and hasattr(job_manager, 'job_started'):
            job_manager.job_started.connect(self._on_job_started)
            job_manager.job_progress.connect(self._on_job_progress)
            job_manager.job_completed.connect(self._on_job_completed)
            job_manager.job_failed.connect(self._on_job_failed)
            job_manager.job_cancelled.connect(self._on_job_cancelled)
    
    def load_data(self) -> None:
        """데이터 로드."""
        # TODO: 실제 데이터 로드 로직
        pass
    
    @property
    def scan_folder(self) -> Optional[Path]:
        """스캔 폴더 반환."""
        return self._scan_folder
    
    @scan_folder.setter
    def scan_folder(self, value: Optional[Path]) -> None:
        """스캔 폴더 설정."""
        self._scan_folder = value
        self.data_changed.emit()
    
    @property
    def is_scanning(self) -> bool:
        """스캔 중 여부 반환."""
        return self._is_scanning
    
    @property
    def progress_count(self) -> int:
        """진행 파일 수 반환."""
        return self._progress_count
    
    @property
    def progress_message(self) -> str:
        """진행 메시지 반환."""
        return self._progress_message
    
    def start_scan(self, folder: Path, extensions: str = "", **options) -> None:
        """스캔 시작."""
        debug_step(
            self._log_sink,
            "scan_view_model_start_scan",
            {
                "folder": str(folder),
                "extensions": extensions,
                "is_scanning": self._is_scanning,
                "has_job_manager": self._job_manager is not None,
            }
        )
        
        if self._is_scanning or not self._job_manager:
            return
        
        # Request DTO 생성
        from app.settings.constants import DEFAULT_TEXT_EXTENSIONS
        from application.dto.scan_request import ScanRequest
        
        # 확장자 문자열 파싱 (빈 문자열이면 기본 텍스트 확장자 사용)
        parsed_extensions = parse_extensions(extensions)
        ext_list: Optional[list[str]] = parsed_extensions if parsed_extensions else DEFAULT_TEXT_EXTENSIONS
        
        request = ScanRequest(
            root_folder=folder,
            extensions=ext_list,
            include_subdirs=options.get("include_subdirs", True),
            include_hidden=options.get("include_hidden", False),
            include_symlinks=options.get("include_symlinks", True),
            incremental=options.get("incremental_scan", True),
        )
        
        self._scan_folder = folder
        self._extension_filter = extensions
        self._include_subdirs = options.get("include_subdirs", True)
        self._include_hidden = options.get("include_hidden", False)
        self._include_symlinks = options.get("include_symlinks", True)
        self._incremental_scan = options.get("incremental_scan", True)
        
        # JobManager를 통한 스캔 시작
        self._current_job_id = self._job_manager.start_scan(request)
        debug_step(
            self._log_sink,
            "scan_view_model_scan_started",
            {"job_id": self._current_job_id}
        )
    
    def _on_job_started(self, job_id: int, job_type: JobType) -> None:
        """Job 시작 핸들러.
        
        Args:
            job_id: Job ID.
            job_type: Job 타입.
        """
        debug_step(
            self._log_sink,
            "scan_view_model_job_started",
            {"job_id": job_id, "job_type": job_type.value}
        )
        
        if job_id != self._current_job_id:
            return
        
        self._is_scanning = True
        self._progress_count = 0
        self._progress_message = "스캔 시작 중..."
        self.data_changed.emit()
        self.progress_updated.emit(0, "스캔 시작 중...")
    
    def _on_job_progress(self, job_id: int, progress: JobProgress) -> None:
        """Job 진행률 핸들러.
        
        Args:
            job_id: Job ID.
            progress: 진행률 정보.
        """
        if job_id != self._current_job_id:
            return
        
        self._progress_count = progress.processed
        self._progress_message = progress.message
        self.progress_updated.emit(0, progress.message)  # 0은 indeterminate 의미
    
    def _on_job_completed(self, job_id: int, result: object) -> None:
        """Job 완료 핸들러.
        
        Args:
            job_id: Job ID.
            result: 스캔 결과 (ScanResult) 또는 중복 탐지 결과 (list).
        """
        # ScanResult 타입인지 확인 (중복 탐지 결과는 list이므로 무시)
        if not isinstance(result, ScanResult):
            return
        
        debug_step(
            self._log_sink,
            "scan_view_model_job_completed",
            {
                "job_id": job_id,
                "total_files": result.total_files,
                "total_bytes": result.total_bytes,
            }
        )
        
        if job_id != self._current_job_id:
            return
        
        self._is_scanning = False
        self._progress_count = result.total_files
        self._progress_message = f"스캔 완료: {result.total_files}개 파일"
        self.data_changed.emit()
        self.progress_updated.emit(0, self._progress_message)
        self.scan_completed.emit(result)
    
    def _on_job_failed(self, job_id: int, error: str) -> None:
        """Job 실패 핸들러.
        
        Args:
            job_id: Job ID.
            error: 에러 메시지.
        """
        debug_step(
            self._log_sink,
            "scan_view_model_job_failed",
            {"job_id": job_id, "error": error}
        )
        
        if job_id != self._current_job_id:
            return
        
        self._is_scanning = False
        self._progress_message = f"오류: {error}"
        self.data_changed.emit()
        self.error_occurred.emit(error)
        self.scan_error.emit(error)
    
    def _on_job_cancelled(self, job_id: int) -> None:
        """Job 취소 핸들러.
        
        Args:
            job_id: Job ID.
        """
        debug_step(
            self._log_sink,
            "scan_view_model_job_cancelled",
            {"job_id": job_id}
        )
        
        if job_id != self._current_job_id:
            return
        
        self._is_scanning = False
        self._progress_message = "스캔 중지됨"
        self.data_changed.emit()
        self.progress_updated.emit(0, "스캔 중지됨")
    
    def stop_scan(self) -> None:
        """스캔 중지."""
        if not self._is_scanning or not self._job_manager or self._current_job_id is None:
            return
        
        # JobManager를 통한 취소
        self._job_manager.cancel(self._current_job_id)
    
    def update_progress(self, progress: int, message: str) -> None:
        """진행률 업데이트 (호환성을 위해 유지)."""
        self._progress_message = message
        self.progress_updated.emit(progress, message)
