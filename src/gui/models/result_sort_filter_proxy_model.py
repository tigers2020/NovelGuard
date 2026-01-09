"""ResultSortFilterProxyModel - Store 기반 필터링/정렬."""

from typing import Optional
from PySide6.QtCore import QSortFilterProxyModel, QModelIndex
from gui.models.result_table_model import ResultTableModel


class ResultSortFilterProxyModel(QSortFilterProxyModel):
    """결과 정렬/필터 프록시 모델.
    
    Store 기반 필터링 및 UserRole 원시값 기반 정렬.
    """
    
    def __init__(self, parent=None) -> None:
        """ResultSortFilterProxyModel 초기화.
        
        Args:
            parent: 부모 객체
        """
        super().__init__(parent)
        
        # 필터 조건
        self._group_type_filter: Optional[str] = None
        self._action_filter: Optional[str] = None
        self._severity_filter: Optional[str] = None
        self._min_size: Optional[int] = None
        self._max_size: Optional[int] = None
        self._encoding_filter: Optional[str] = None
        self._text_search: Optional[str] = None
    
    def setGroupTypeFilter(self, group_type: Optional[str]) -> None:
        """그룹 타입 필터 설정.
        
        Args:
            group_type: 그룹 타입 (None이면 필터 해제)
        """
        self._group_type_filter = group_type
        self.invalidateFilter()
    
    def setActionFilter(self, action: Optional[str]) -> None:
        """액션 필터 설정.
        
        Args:
            action: 액션 (None이면 필터 해제)
        """
        self._action_filter = action
        self.invalidateFilter()
    
    def setSeverityFilter(self, severity: Optional[str]) -> None:
        """심각도 필터 설정.
        
        Args:
            severity: 심각도 (None이면 필터 해제)
        """
        self._severity_filter = severity
        self.invalidateFilter()
    
    def setSizeRangeFilter(self, min_size: Optional[int] = None, max_size: Optional[int] = None) -> None:
        """크기 범위 필터 설정.
        
        Args:
            min_size: 최소 크기 (None이면 제한 없음)
            max_size: 최대 크기 (None이면 제한 없음)
        """
        self._min_size = min_size
        self._max_size = max_size
        self.invalidateFilter()
    
    def setEncodingFilter(self, encoding: Optional[str]) -> None:
        """인코딩 필터 설정.
        
        Args:
            encoding: 인코딩 (None이면 필터 해제)
        """
        self._encoding_filter = encoding
        self.invalidateFilter()
    
    def setTextSearch(self, text: Optional[str]) -> None:
        """텍스트 검색 설정.
        
        Args:
            text: 검색 텍스트 (None이면 검색 해제)
        """
        self._text_search = text.lower() if text else None
        self.invalidateFilter()
    
    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
        """행 필터링 판정.
        
        Args:
            source_row: 소스 행 인덱스
            source_parent: 소스 부모 인덱스
        
        Returns:
            필터 통과 여부
        """
        source_model = self.sourceModel()
        if not isinstance(source_model, ResultTableModel):
            return True
        
        # 인덱스로 데이터 접근
        index = source_model.index(source_row, 0, source_parent)
        row = source_model._rows[source_row] if source_row < len(source_model._rows) else None
        
        if row is None:
            return False
        
        # 그룹 타입 필터
        if self._group_type_filter and row.group_type != self._group_type_filter:
            return False
        
        # 액션 필터
        if self._action_filter and row.planned_action != self._action_filter:
            return False
        
        # 크기 범위 필터
        if self._min_size is not None and row.size < self._min_size:
            return False
        if self._max_size is not None and row.size > self._max_size:
            return False
        
        # 인코딩 필터
        if self._encoding_filter and row.encoding != self._encoding_filter:
            return False
        
        # 텍스트 검색
        if self._text_search:
            search_text = row.short_path.lower()
            if self._text_search not in search_text:
                return False
        
        return True
    
    def lessThan(self, left: QModelIndex, right: QModelIndex) -> bool:
        """정렬 비교 (UserRole 원시값 사용).
        
        Args:
            left: 왼쪽 인덱스
            right: 오른쪽 인덱스
        
        Returns:
            left < right 여부
        """
        source_model = self.sourceModel()
        if not isinstance(source_model, ResultTableModel):
            return super().lessThan(left, right)
        
        column = left.column()
        
        # 정렬용 원시값 사용
        if column == ResultTableModel.COLUMN_SIZE:
            left_value = source_model.data(left, ResultTableModel.ROLE_SIZE)
            right_value = source_model.data(right, ResultTableModel.ROLE_SIZE)
            return left_value < right_value
        elif column == ResultTableModel.COLUMN_SIMILARITY:
            left_value = source_model.data(left, ResultTableModel.ROLE_SIMILARITY)
            right_value = source_model.data(right, ResultTableModel.ROLE_SIMILARITY)
            return left_value < right_value
        
        # 기본 정렬
        return super().lessThan(left, right)

