"""Undo/Rollback 탭 ViewModel."""
from typing import Optional

from PySide6.QtCore import QObject

from gui.view_models.base_view_model import BaseViewModel


class UndoViewModel(BaseViewModel):
    """Undo/Rollback 탭 ViewModel."""
    
    def __init__(self, parent: Optional[QObject] = None) -> None:
        """Undo ViewModel 초기화."""
        super().__init__(parent)
        
        # 실행 기록
        self._action_history: list = []
    
    def load_data(self) -> None:
        """데이터 로드."""
        # TODO: 실제 실행 기록 로드 로직
        
        self.data_changed.emit()
    
    def undo_action(self, action_id: str) -> None:
        """작업 되돌리기."""
        # TODO: 실제 Undo 로직 호출
        
        self.data_changed.emit()
    
    def reset_all(self) -> None:
        """모든 작업 초기화."""
        # TODO: 실제 초기화 로직 호출
        
        self.data_changed.emit()
