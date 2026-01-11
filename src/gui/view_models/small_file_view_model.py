"""작은 파일 정리 탭 ViewModel."""
from typing import Optional

from PySide6.QtCore import QObject

from gui.view_models.base_view_model import BaseViewModel


class SmallFileViewModel(BaseViewModel):
    """작은 파일 정리 탭 ViewModel."""
    
    def __init__(self, parent: Optional[QObject] = None) -> None:
        """작은 파일 ViewModel 초기화."""
        super().__init__(parent)
        
        # 설정
        self._size_threshold: str = "< 1 KB"
        
        # 결과
        self._small_files: list = []
    
    def load_data(self) -> None:
        """데이터 로드."""
        # TODO: 실제 데이터 로드 로직 (UseCase 호출)
        pass
    
    def analyze_small_files(self) -> None:
        """작은 파일 분석."""
        # TODO: 실제 분석 로직 호출 (UseCase)
        
        self.data_changed.emit()
