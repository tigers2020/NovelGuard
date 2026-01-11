"""스캔 워커 스레드."""
from typing import Optional

from PySide6.QtCore import QObject, QThread, Signal

from application.dto.scan_request import ScanRequest
from application.dto.scan_result import ScanResult
from application.ports.file_scanner import FileScanner
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
        parent: Optional[QObject] = None
    ) -> None:
        """스캔 워커 초기화.
        
        Args:
            scanner: 파일 스캐너 (Port 인터페이스).
            request: 스캔 요청 DTO.
            parent: 부모 객체.
        """
        super().__init__(parent)
        self._scanner = scanner
        self._request = request
        self._use_case = ScanFolderUseCase(scanner)
        self._cancelled = False
    
    def cancel(self) -> None:
        """스캔 취소."""
        self._cancelled = True
        # Scanner에도 취소 신호 전달 (Protocol 계약)
        self._scanner.cancel()
    
    def run(self) -> None:
        """워커 실행."""
        try:
            result = self._use_case.execute(
                self._request,
                progress_callback=lambda count, msg: self.scan_progress.emit(count, msg)
            )
            if not self._cancelled:
                self.scan_completed.emit(result)
        except Exception as e:
            if not self._cancelled:
                self.scan_error.emit(str(e))
