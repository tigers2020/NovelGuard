"""ScanWorker - 파일 스캔 Worker."""

from pathlib import Path
from PySide6.QtCore import QThread, Signal
from usecases.scan_files import ScanFilesUseCase
from gui.signals.result_signals import ResultSignals
from common.logging import setup_logging

logger = setup_logging()


class ScanWorker(QThread):
    """파일 스캔 Worker.
    
    usecase 호출 및 signals emit.
    """
    
    def __init__(
        self,
        usecase: ScanFilesUseCase,
        signals: ResultSignals,
        root_path: Path,
        parent=None
    ) -> None:
        """ScanWorker 초기화.
        
        Args:
            usecase: ScanFilesUseCase
            signals: ResultSignals
            root_path: 스캔 대상 경로
            parent: 부모 객체
        """
        super().__init__(parent)
        self.usecase = usecase
        self.signals = signals
        self.root_path = root_path
    
    def run(self) -> None:
        """Worker 실행."""
        try:
            def progress_callback(current: int, total: int, current_path: Path) -> None:
                """진행 상황 콜백."""
                self.signals.scan_progress.emit("스캔 중", current, total, str(current_path))
            
            # usecase 실행
            records = self.usecase.execute(self.root_path, progress_callback)
            
            # FileRow 변환 (간단한 변환, 실제로는 도메인 모델에서 FileRow로 변환 필요)
            from gui.view_models.file_row import FileRow
            rows = []
            for record in records:
                row = FileRow(
                    file_id=record.file_id,
                    short_path=str(record.path),
                    size=record.size,
                    mtime=record.mtime,
                    encoding=record.encoding_detected
                )
                rows.append(row)
            
            # Signal emit
            self.signals.rows_appended.emit(rows)
            
        except Exception as e:
            logger.error(f"스캔 Worker 오류: {e}")
            self.signals.log_event.emit("ERROR", f"스캔 실패: {e}", None)

