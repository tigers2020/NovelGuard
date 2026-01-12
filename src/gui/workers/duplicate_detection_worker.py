"""중복 탐지 워커 스레드."""
from datetime import datetime
from typing import Optional, TYPE_CHECKING

from PySide6.QtCore import QObject, QThread, Signal

from application.dto.duplicate_detection_request import DuplicateDetectionRequest
from application.dto.duplicate_group_result import DuplicateGroupResult
from application.dto.job_types import JobProgress
from application.dto.log_entry import LogEntry
from application.ports.index_repository import IIndexRepository
from application.ports.log_sink import ILogSink
from application.use_cases.duplicate_detection.duplicate_detection_pipeline import (
    DuplicateDetectionPipeline
)
from application.use_cases.duplicate_detection.stages.base_stage import PipelineError
from application.utils.debug_logger import debug_step
from domain.services.blocking_service import BlockingService
from domain.services.containment_detector import ContainmentDetector
from domain.services.filename_parser import FilenameParser

if TYPE_CHECKING:
    from gui.models.file_data_store import FileDataStore


class DuplicateDetectionWorker(QThread):
    """중복 탐지 워커 스레드.
    
    QThread를 상속하여 별도 스레드에서 중복 탐지 작업을 수행.
    단계별 진행률 추적 및 취소 지원.
    """
    
    duplicate_completed = Signal(list)
    """중복 탐지 완료 시그널 (DuplicateGroupResult 리스트)."""
    
    duplicate_error = Signal(str)
    """중복 탐지 오류 시그널."""
    
    duplicate_progress = Signal(JobProgress)
    """중복 탐지 진행률 시그널 (JobProgress)."""
    
    def __init__(
        self,
        request: DuplicateDetectionRequest,
        index_repository: Optional[IIndexRepository] = None,
        log_sink: Optional[ILogSink] = None,
        file_data_store: Optional["FileDataStore"] = None,
        parent: Optional[QObject] = None
    ) -> None:
        """중복 탐지 워커 초기화.
        
        Args:
            request: 중복 탐지 요청 DTO.
            index_repository: 인덱스 저장소 (선택적).
            log_sink: 로그 싱크 (선택적).
            file_data_store: 파일 데이터 저장소 (선택적).
            parent: 부모 객체.
        """
        super().__init__(parent)
        self._request = request
        self._index_repository = index_repository
        self._log_sink = log_sink
        self._file_data_store = file_data_store
        self._cancelled = False
        
        # 도메인 서비스 초기화
        self._filename_parser = FilenameParser(log_sink=log_sink)
        self._blocking_service = BlockingService(filename_parser=self._filename_parser, log_sink=log_sink)
        self._containment_detector = ContainmentDetector(log_sink=log_sink)
        
        # Pipeline 초기화
        self._pipeline: Optional[DuplicateDetectionPipeline] = None
        if index_repository:
            self._pipeline = DuplicateDetectionPipeline(
                filename_parser=self._filename_parser,
                blocking_service=self._blocking_service,
                containment_detector=self._containment_detector,
                index_repository=index_repository,
                file_data_store=file_data_store,
                log_sink=log_sink
            )
    
    def cancel(self) -> None:
        """중복 탐지 취소."""
        debug_step(
            self._log_sink,
            "duplicate_detection_worker_cancel",
            {}
        )
        self._cancelled = True
    
    def run(self) -> None:
        """워커 실행."""
        debug_step(
            self._log_sink,
            "duplicate_detection_worker_run_start",
            {
                "run_id": self._request.run_id,
                "enable_exact": self._request.enable_exact,
                "enable_version": self._request.enable_version,
                "enable_containment": self._request.enable_containment,
                "enable_near": self._request.enable_near,
            }
        )
        
        if not self._index_repository:
            error_msg = "IndexRepository is required for duplicate detection"
            if self._log_sink:
                self._log_sink.write(LogEntry(
                    timestamp=datetime.now(),
                    level="ERROR",
                    message=error_msg,
                    context={}
                ))
            self.duplicate_error.emit(error_msg)
            return
        
        if not self._pipeline:
            error_msg = "Pipeline is not initialized"
            if self._log_sink:
                self._log_sink.write(LogEntry(
                    timestamp=datetime.now(),
                    level="ERROR",
                    message=error_msg,
                    context={}
                ))
            self.duplicate_error.emit(error_msg)
            return
        
        try:
            # 파이프라인 실행 (진행률 콜백 제공)
            results = self._pipeline.execute(
                self._request,
                progress_callback=self._on_progress,
                cancellation_check=self._check_cancelled
            )
            
            if not self._cancelled:
                debug_step(
                    self._log_sink,
                    "duplicate_detection_worker_completed",
                    {
                        "results_count": len(results)
                    }
                )
                self.duplicate_completed.emit(results)
        
        except PipelineError as e:
            if not self._cancelled:
                if self._log_sink:
                    self._log_sink.write(LogEntry(
                        timestamp=datetime.now(),
                        level="ERROR",
                        message=f"Duplicate detection pipeline error: {e}",
                        context={
                            "error_type": type(e).__name__,
                        }
                    ))
                    debug_step(
                        self._log_sink,
                        "duplicate_detection_worker_error",
                        {
                            "error": str(e),
                            "error_type": type(e).__name__,
                        }
                    )
                self.duplicate_error.emit(str(e))
        
        except Exception as e:
            if not self._cancelled:
                # 로그 기록
                if self._log_sink:
                    self._log_sink.write(LogEntry(
                        timestamp=datetime.now(),
                        level="ERROR",
                        message=f"Duplicate detection failed: {e}",
                        context={
                            "error_type": type(e).__name__,
                        }
                    ))
                    debug_step(
                        self._log_sink,
                        "duplicate_detection_worker_error",
                        {
                            "error": str(e),
                            "error_type": type(e).__name__,
                        }
                    )
                self.duplicate_error.emit(str(e))
    
    def _on_progress(self, processed: int, total: int, message: str) -> None:
        """진행률 콜백.
        
        Args:
            processed: 처리된 단계 인덱스.
            total: 총 단계 수.
            message: 진행 메시지.
        """
        if not self._cancelled:
            progress = JobProgress(
                processed=processed,
                total=total,
                message=message
            )
            self.duplicate_progress.emit(progress)
    
    def _check_cancelled(self) -> bool:
        """취소 여부 확인.
        
        Returns:
            취소되었으면 True.
        """
        return self._cancelled
