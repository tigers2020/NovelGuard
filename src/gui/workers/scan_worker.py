"""스캔 워커 스레드."""
from datetime import datetime
from typing import Optional

from PySide6.QtCore import QObject, QThread, Signal

from application.dto.log_entry import LogEntry
from application.dto.scan_request import ScanRequest
from application.dto.scan_result import ScanResult
from application.ports.file_scanner import FileScanner
from application.ports.index_repository import IIndexRepository
from application.ports.log_sink import ILogSink
from application.utils.debug_logger import debug_step
from application.use_cases.scan_folder import ScanFolderUseCase


class ScanWorker(QThread):
    """스캔 워커 스레드.
    
    QThread를 상속하여 별도 스레드에서 스캔 작업을 수행.
    PreviewWorker와 동일한 패턴 사용.
    """
    
    scan_completed = Signal(ScanResult)
    """스캔 완료 시그널."""
    
    scan_error = Signal(str)
    """스캔 오류 시그널."""
    
    scan_progress = Signal(int, str)
    """스캔 진행률 시그널 (processed_count, message)."""
    
    def __init__(
        self,
        scanner: FileScanner,
        request: ScanRequest,
        index_repository: Optional[IIndexRepository] = None,
        log_sink: Optional[ILogSink] = None,
        parent: Optional[QObject] = None
    ) -> None:
        """스캔 워커 초기화.
        
        Args:
            scanner: 파일 스캐너 (Port 인터페이스).
            request: 스캔 요청 DTO.
            index_repository: 인덱스 저장소 (선택적).
            log_sink: 로그 싱크 (선택적).
            parent: 부모 객체.
        """
        super().__init__(parent)
        self._scanner = scanner
        self._request = request
        self._index_repository = index_repository
        self._log_sink = log_sink
        self._use_case = ScanFolderUseCase(scanner, index_repository, log_sink)
        self._cancelled = False
    
    def cancel(self) -> None:
        """스캔 취소."""
        debug_step(self._log_sink, "scan_worker_cancel")
        self._cancelled = True
        # Scanner에도 취소 신호 전달 (Protocol 계약)
        self._scanner.cancel()
    
    def run(self) -> None:
        """워커 실행."""
        debug_step(
            self._log_sink,
            "scan_worker_run_start",
            {
                "root_folder": str(self._request.root_folder),
                "extensions": self._request.extensions,
                "include_subdirs": self._request.include_subdirs,
            }
        )
        
        try:
            result = self._use_case.execute(
                self._request,
                progress_callback=lambda count, msg: self.scan_progress.emit(count, msg)
            )
            if not self._cancelled:
                debug_step(
                    self._log_sink,
                    "scan_worker_completed",
                    {
                        "total_files": result.total_files,
                        "total_bytes": result.total_bytes,
                        "elapsed_ms": result.elapsed_ms,
                    }
                )
                self.scan_completed.emit(result)
        except Exception as e:
            if not self._cancelled:
                # 로그 기록
                if self._log_sink:
                    self._log_sink.write(LogEntry(
                        timestamp=datetime.now(),
                        level="ERROR",
                        message=f"Scan failed: {e}",
                        context={"error_type": type(e).__name__}
                    ))
                    debug_step(
                        self._log_sink,
                        "scan_worker_error",
                        {
                            "error": str(e),
                            "error_type": type(e).__name__,
                        }
                    )
                self.scan_error.emit(str(e))
