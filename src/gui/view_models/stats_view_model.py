"""통계 및 리포트 탭 ViewModel."""
from typing import Optional

from PySide6.QtCore import QObject

from gui.view_models.base_view_model import BaseViewModel


class StatsViewModel(BaseViewModel):
    """통계 및 리포트 탭 ViewModel."""
    
    def __init__(self, parent: Optional[QObject] = None) -> None:
        """통계 ViewModel 초기화."""
        super().__init__(parent)
        
        # 통계
        self._duplicate_groups: int = 0
        self._small_files: int = 0
        self._saved_size_gb: float = 0.0
    
    def load_data(self) -> None:
        """데이터 로드."""
        # TODO: 실제 데이터 로드 로직 (UseCase 호출)
        pass
    
    def export_excel(self, file_path: str) -> None:
        """Excel 리포트 내보내기."""
        # TODO: 실제 Excel 내보내기 로직
        
        self.data_changed.emit()
    
    def export_pdf(self, file_path: str) -> None:
        """PDF 리포트 내보내기."""
        # TODO: 실제 PDF 내보내기 로직
        
        self.data_changed.emit()
