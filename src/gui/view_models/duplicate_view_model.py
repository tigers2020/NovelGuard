"""중복 파일 정리 탭 ViewModel."""
from typing import Optional

from PySide6.QtCore import QObject

from gui.view_models.base_view_model import BaseViewModel


class DuplicateViewModel(BaseViewModel):
    """중복 파일 정리 탭 ViewModel."""
    
    def __init__(self, parent: Optional[QObject] = None) -> None:
        """중복 ViewModel 초기화."""
        super().__init__(parent)
        
        # 설정
        self._exact_duplicate: bool = True
        self._near_duplicate: bool = True
        self._include_relation: bool = True
        self._similarity_threshold: int = 85
        self._conflict_policy: str = "rename"
        
        # 결과
        self._duplicate_groups: list = []
    
    def load_data(self) -> None:
        """데이터 로드."""
        # TODO: 실제 데이터 로드 로직 (UseCase 호출)
        pass
    
    def start_detection(self) -> None:
        """중복 탐지 시작."""
        # TODO: 실제 중복 탐지 로직 호출 (UseCase)
        # find_duplicates_usecase = ...
        # result = find_duplicates_usecase.execute(...)
        
        self.data_changed.emit()
    
    def apply_changes(self, selected_groups: list) -> None:
        """변경 사항 적용."""
        # TODO: 실제 적용 로직 호출 (UseCase)
        # build_action_plan_usecase = ...
        # plan = build_action_plan_usecase.execute(...)
        
        self.data_changed.emit()
