# STUB: Not wired yet
"""작업 로그 탭 ViewModel."""
from typing import Optional

from PySide6.QtCore import QObject

from gui.view_models.base_view_model import BaseViewModel


class LogsViewModel(BaseViewModel):
    """작업 로그 탭 ViewModel."""
    
    def __init__(self, parent: Optional[QObject] = None) -> None:
        """로그 ViewModel 초기화."""
        super().__init__(parent)
        
        # 로그 목록
        self._logs: list[str] = []
    
    def load_data(self) -> None:
        """데이터 로드."""
        # TODO: 실제 로그 로드 로직
        
        # 샘플 로그 추가
        self._logs = [
            "[14:23:45] [INFO] 스캔 시작",
            "[14:23:46] [INFO] 워커 스레드 8개 초기화",
            "[14:24:45] [WARN] 인코딩 감지 실패",
            "[14:25:45] [ERROR] 파일 읽기 실패",
        ]
        self.data_changed.emit()
    
    def add_log(self, log: str) -> None:
        """로그 추가."""
        self._logs.append(log)
        self.data_changed.emit()
    
    def clear_logs(self) -> None:
        """로그 지우기."""
        self._logs.clear()
        self.data_changed.emit()
    
    def export_logs(self, file_path: str) -> None:
        """로그 내보내기."""
        # TODO: 실제 로그 내보내기 로직
        from app.settings.constants import Constants
        with open(file_path, "w", encoding=Constants.DEFAULT_ENCODING) as f:
            f.write("\n".join(self._logs))
        
        self.data_changed.emit()
    
    @property
    def logs(self) -> list[str]:
        """로그 목록 반환."""
        return self._logs
