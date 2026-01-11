"""스캔 탭 ViewModel."""
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, QThread, Signal

from application.dto.scan_result import ScanResult
from gui.view_models.base_view_model import BaseViewModel


class ScanViewModel(BaseViewModel):
    """스캔 탭 ViewModel."""
    
    # 신규 시그널 추가
    scan_completed = Signal(ScanResult)  # 스캔 완료 시그널
    scan_error = Signal(str)  # 스캔 오류 시그널
    
    def __init__(self, parent: Optional[QObject] = None) -> None:
        """스캔 ViewModel 초기화."""
        super().__init__(parent)
        
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
        
        # Worker
        self._scan_worker: Optional[QThread] = None
    
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
        if self._is_scanning:
            return
        
        # Request DTO 생성
        from app.settings.constants import DEFAULT_TEXT_EXTENSIONS
        from application.dto.scan_request import ScanRequest
        
        ext_list: Optional[list[str]] = None
        if extensions.strip():
            ext_list = [e.strip() for e in extensions.split(',') if e.strip()]
            ext_list = [e if e.startswith('.') else f'.{e}' for e in ext_list]
        elif extensions == "":
            ext_list = DEFAULT_TEXT_EXTENSIONS
        
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
        
        self._is_scanning = True
        self._progress_count = 0
        self._progress_message = "스캔 시작 중..."
        
        self.data_changed.emit()
        self.progress_updated.emit(0, "스캔 시작 중...")
        
        # Worker 생성 및 시작
        from infrastructure.fs.scanner import FileSystemScanner
        from gui.workers.scan_worker import ScanWorker
        
        scanner = FileSystemScanner()
        self._scan_worker = ScanWorker(scanner, request, parent=self)
        self._scan_worker.scan_completed.connect(self._on_scan_completed)
        self._scan_worker.scan_error.connect(self._on_scan_error)
        self._scan_worker.scan_progress.connect(self._on_scan_progress)
        self._scan_worker.start()
    
    def _on_scan_completed(self, result: ScanResult) -> None:
        """스캔 완료 핸들러."""
        self._is_scanning = False
        self._progress_count = result.total_files
        self._progress_message = f"스캔 완료: {result.total_files}개 파일"
        self.data_changed.emit()
        self.progress_updated.emit(0, self._progress_message)
        self.scan_completed.emit(result)
    
    def _on_scan_error(self, error_message: str) -> None:
        """스캔 오류 핸들러."""
        self._is_scanning = False
        self._progress_message = f"오류: {error_message}"
        self.data_changed.emit()
        self.error_occurred.emit(error_message)
        self.scan_error.emit(error_message)
    
    def _on_scan_progress(self, count: int, message: str) -> None:
        """스캔 진행률 핸들러."""
        self._progress_count = count
        self._progress_message = message
        self.progress_updated.emit(0, message)  # 0은 indeterminate 의미
    
    def stop_scan(self) -> None:
        """스캔 중지."""
        if not self._is_scanning:
            return
        
        if self._scan_worker and self._scan_worker.isRunning():
            # Worker의 cancel() 호출 (scanner.cancel()까지 전달됨)
            self._scan_worker.cancel()
            # 타임아웃으로 UI freeze 방지 (최대 200ms 대기)
            self._scan_worker.wait(200)
        
        self._is_scanning = False
        self._progress_message = "스캔 중지됨"
        self.data_changed.emit()
        self.progress_updated.emit(0, "스캔 중지됨")
    
    def update_progress(self, progress: int, message: str) -> None:
        """진행률 업데이트 (호환성을 위해 유지)."""
        self._progress_message = message
        self.progress_updated.emit(progress, message)
