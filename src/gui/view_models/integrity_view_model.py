"""무결성 확인 탭 ViewModel."""
from typing import Optional

from PySide6.QtCore import QObject

from gui.view_models.base_view_model import BaseViewModel


class IntegrityViewModel(BaseViewModel):
    """무결성 확인 탭 ViewModel."""
    
    def __init__(self, parent: Optional[QObject] = None) -> None:
        """무결성 ViewModel 초기화."""
        super().__init__(parent)
        
        # 통계
        self._normal_files: int = 0
        self._warning_files: int = 0
        self._error_files: int = 0
        
        # 결과
        self._integrity_issues: list = []
    
    def load_data(self) -> None:
        """데이터 로드."""
        # TODO: 실제 데이터 로드 로직 (UseCase 호출)
        pass
    
    def check_integrity(self) -> None:
        """무결성 검사."""
        # TODO: 실제 무결성 검사 로직 호출 (UseCase)
        # check_integrity_usecase = ...
        # result = check_integrity_usecase.execute(...)
        
        self.data_changed.emit()
    
    def auto_fix(self, issue_ids: list) -> None:
        """자동 수정."""
        # TODO: 실제 자동 수정 로직 호출
        
        self.data_changed.emit()
