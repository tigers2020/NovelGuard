# STUB: Not wired yet
"""인코딩 통일 탭 ViewModel."""
from typing import Optional

from PySide6.QtCore import QObject

from gui.view_models.base_view_model import BaseViewModel


class EncodingViewModel(BaseViewModel):
    """인코딩 통일 탭 ViewModel."""
    
    def __init__(self, parent: Optional[QObject] = None) -> None:
        """인코딩 ViewModel 초기화."""
        super().__init__(parent)
        
        # 설정
        self._target_encoding: str = "UTF-8 (LF)"
        
        # 결과
        self._encoding_stats: dict = {}
    
    def load_data(self) -> None:
        """데이터 로드."""
        # TODO: 실제 데이터 로드 로직 (UseCase 호출)
        pass
    
    def analyze_encoding(self) -> None:
        """인코딩 분석."""
        # TODO: 실제 인코딩 분석 로직 호출
        
        self.data_changed.emit()
    
    def convert_to_utf8(self) -> None:
        """UTF-8 변환."""
        # TODO: 실제 변환 로직 호출
        
        self.data_changed.emit()
