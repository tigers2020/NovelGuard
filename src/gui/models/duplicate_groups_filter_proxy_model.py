"""중복 그룹 필터 프록시 모델."""
from typing import Optional

from PySide6.QtCore import QModelIndex, QSortFilterProxyModel, Qt

from application.dto.duplicate_group_result import DuplicateGroupResult
from gui.models.duplicate_groups_table_model import DuplicateGroupsTableModel


class DuplicateGroupsFilterProxyModel(QSortFilterProxyModel):
    """중복 그룹 필터 프록시 모델.
    
    타입 필터, 신뢰도 필터, 검색 필터를 지원.
    """
    
    def __init__(self, parent=None) -> None:
        """중복 그룹 필터 프록시 모델 초기화.
        
        Args:
            parent: 부모 객체.
        """
        super().__init__(parent)
        
        # 필터 상태
        self._type_filter: Optional[str] = None  # None이면 전체
        self._min_confidence: float = 0.0  # 최소 신뢰도 (0.0 ~ 1.0)
        self._search_text: str = ""  # 검색 텍스트
    
    def set_type_filter(self, type_str: Optional[str]) -> None:
        """타입 필터 설정.
        
        Args:
            type_str: 타입 문자열 (None이면 전체).
        """
        if self._type_filter != type_str:
            self._type_filter = type_str
            self.invalidateFilter()
    
    def set_min_confidence(self, confidence: float) -> None:
        """최소 신뢰도 설정.
        
        Args:
            confidence: 최소 신뢰도 (0.0 ~ 1.0).
        """
        if self._min_confidence != confidence:
            self._min_confidence = confidence
            self.invalidateFilter()
    
    def set_search_text(self, text: str) -> None:
        """검색 텍스트 설정.
        
        Args:
            text: 검색 텍스트.
        """
        if self._search_text != text:
            self._search_text = text.strip().lower()
            self.invalidateFilter()
    
    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
        """행 필터링.
        
        Args:
            source_row: 소스 모델의 행 인덱스.
            source_parent: 소스 모델의 부모 인덱스.
            
        Returns:
            True이면 행을 표시, False이면 숨김.
        """
        source_model = self.sourceModel()
        if not isinstance(source_model, DuplicateGroupsTableModel):
            return True
        
        # 결과 가져오기
        result = source_model.get_result(source_row)
        if not result:
            return False
        
        # 타입 필터
        if self._type_filter and self._type_filter != "전체":
            if result.duplicate_type != self._type_filter:
                return False
        
        # 신뢰도 필터
        if result.confidence < self._min_confidence:
            return False
        
        # 검색 필터
        if self._search_text:
            # 타입, 그룹 ID, 작품명/제목에서 검색
            type_text = result.duplicate_type.lower()
            group_id_text = str(result.group_id)
            # source_model의 _extract_key_title 메서드 호출
            key_title = source_model.data(
                source_model.index(source_row, DuplicateGroupsTableModel.COL_KEY_TITLE),
                Qt.DisplayRole
            )
            key_title_text = (key_title or "").lower()
            
            if (self._search_text not in type_text and
                self._search_text not in group_id_text and
                self._search_text not in key_title_text):
                return False
        
        return True
