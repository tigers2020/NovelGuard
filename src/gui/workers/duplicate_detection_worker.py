"""중복 탐지 워커 스레드."""

from datetime import datetime
from typing import Optional

from PySide6.QtCore import QObject, QThread, Signal

from application.dto.duplicate_detection_request import DuplicateDetectionRequest
from application.dto.job_types import JobProgress
from application.dto.log_entry import LogEntry
from application.ports.log_sink import ILogSink
from application.use_cases.duplicate_detection.duplicate_detection_pipeline import (
    DuplicateDetectionPipeline,
)
from application.use_cases.duplicate_detection.stages.base_stage import PipelineError
from application.utils.debug_logger import debug_step


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
        *,
        pipeline: DuplicateDetectionPipeline | None = None,
        log_sink: Optional[ILogSink] = None,
        parent: Optional[QObject] = None,
    ) -> None:
        """중복 탐지 워커 초기화.

        Args:
            request: 중복 탐지 요청 DTO.
            pipeline: 조립된 중복 탐지 파이프라인 (composition root에서 주입).
            log_sink: 로그 싱크 (선택적).
            parent: 부모 QObject.
        """
        super().__init__(parent)
        self._request = request
        self._pipeline = pipeline
        self._log_sink = log_sink
        self._cancelled = False

    def cancel(self) -> None:
        """중복 탐지 취소."""
        debug_step(self._log_sink, "duplicate_detection_worker_cancel", {})
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
            },
        )

        if not self._pipeline:
            error_msg = "Duplicate detection pipeline is required"
            if self._log_sink:
                self._log_sink.write(
                    LogEntry(timestamp=datetime.now(), level="ERROR", message=error_msg, context={})
                )
            self.duplicate_error.emit(error_msg)
            return

        try:
            results = self._pipeline.execute(
                self._request,
                progress_callback=self._on_progress,
                cancellation_check=self._check_cancelled,
            )

            if not self._cancelled:
                debug_step(
                    self._log_sink,
                    "duplicate_detection_worker_completed",
                    {"results_count": len(results)},
                )
                self.duplicate_completed.emit(results)

        except PipelineError as e:
            if not self._cancelled:
                if self._log_sink:
                    self._log_sink.write(
                        LogEntry(
                            timestamp=datetime.now(),
                            level="ERROR",
                            message=f"Duplicate detection pipeline error: {e}",
                            context={"error_type": type(e).__name__},
                        )
                    )
                    debug_step(
                        self._log_sink,
                        "duplicate_detection_worker_error",
                        {"error": str(e), "error_type": type(e).__name__},
                    )
                self.duplicate_error.emit(str(e))

        except Exception as e:
            if not self._cancelled:
                if self._log_sink:
                    self._log_sink.write(
                        LogEntry(
                            timestamp=datetime.now(),
                            level="ERROR",
                            message=f"Duplicate detection failed: {e}",
                            context={"error_type": type(e).__name__},
                        )
                    )
                    debug_step(
                        self._log_sink,
                        "duplicate_detection_worker_error",
                        {"error": str(e), "error_type": type(e).__name__},
                    )
                self.duplicate_error.emit(str(e))

    def _on_progress(self, processed: int, total: int, message: str) -> None:
        """진행률 콜백."""
        if not self._cancelled:
            progress = JobProgress(processed=processed, total=total, message=message)
            self.duplicate_progress.emit(progress)

    def _check_cancelled(self) -> bool:
        """취소 여부 확인."""
        return self._cancelled
