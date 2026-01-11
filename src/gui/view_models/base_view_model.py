"""기본 ViewModel 클래스."""
from typing import Optional

from PySide6.QtCore import QObject, Signal


class BaseViewModel(QObject):
    """기본 ViewModel - 모든 ViewModel의 기본 클래스."""
    
    # 시그널 정의
    data_changed = Signal()  # 데이터 변경 시 발생
    error_occurred = Signal(str)  # 에러 발생 시 (에러 메시지)
    progress_updated = Signal(int, str)  # 진행률 업데이트 시 (진행률 %, 메시지)
    
    def __init__(self, parent: Optional[QObject] = None) -> None:
        """기본 ViewModel 초기화."""
        super().__init__(parent)
    
    def load_data(self) -> None:
        """데이터 로드."""
        raise NotImplementedError("Subclass must implement load_data")
    
    def refresh(self) -> None:
        """데이터 새로고침."""
        self.load_data()
