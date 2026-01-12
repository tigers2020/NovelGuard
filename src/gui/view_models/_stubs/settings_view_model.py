# STUB: Not wired yet
"""설정 탭 ViewModel."""
from typing import Optional

from PySide6.QtCore import QObject

from gui.view_models.base_view_model import BaseViewModel


class SettingsViewModel(BaseViewModel):
    """설정 탭 ViewModel."""
    
    def __init__(self, parent: Optional[QObject] = None) -> None:
        """설정 ViewModel 초기화."""
        super().__init__(parent)
        
        # 설정
        self._worker_threads: str = "8"
        self._cache_size_mb: int = 512
    
    def load_data(self) -> None:
        """데이터 로드."""
        # TODO: 실제 설정 로드 로직 (파일 또는 DB에서)
        
        self.data_changed.emit()
    
    def save_settings(self) -> None:
        """설정 저장."""
        # TODO: 실제 설정 저장 로직 (파일 또는 DB에)
        
        self.data_changed.emit()
    
    def reset_to_defaults(self) -> None:
        """기본값으로 복원."""
        self._worker_threads = "8"
        self._cache_size_mb = 512
        self.data_changed.emit()
