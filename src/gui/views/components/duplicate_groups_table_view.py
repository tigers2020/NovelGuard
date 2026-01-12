"""중복 그룹 테이블 뷰 컴포넌트."""
from typing import Optional, TYPE_CHECKING

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QGroupBox,
    QHeaderView,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from gui.models.duplicate_groups_table_model import DuplicateGroupsTableModel

if TYPE_CHECKING:
    from gui.models.file_data_store import FileDataStore


class DuplicateGroupsTableView(QWidget):
    """중복 그룹 테이블 뷰 위젯."""
    
    # 시그널
    group_selected = Signal(int)  # group_id
    
    def __init__(self, parent: Optional[QWidget] = None, file_data_store: "FileDataStore" = None) -> None:
        """중복 그룹 테이블 뷰 초기화.
        
        Args:
            parent: 부모 위젯.
            file_data_store: 파일 데이터 저장소 (필수).
        """
        super().__init__(parent)
        if file_data_store is None:
            raise ValueError("file_data_store is required")
        
        # 모델 생성
        self._model = DuplicateGroupsTableModel(self, file_data_store=file_data_store)
        
        # 프록시 모델 (필터/정렬용)
        from gui.models.duplicate_groups_filter_proxy_model import DuplicateGroupsFilterProxyModel
        self._proxy_model = DuplicateGroupsFilterProxyModel(self)
        self._proxy_model.setSourceModel(self._model)
        
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self) -> None:
        """UI 설정."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 그룹 박스
        group = QGroupBox("중복 그룹")
        group.setObjectName("settingsGroup")
        
        group_layout = QVBoxLayout(group)
        group_layout.setContentsMargins(0, 0, 0, 0)
        group_layout.setSpacing(0)
        
        # 테이블 뷰 생성
        self._table_view = QTableView()
        self._table_view.setModel(self._proxy_model)
        
        # 테이블 설정
        self._table_view.setSelectionBehavior(QTableView.SelectRows)
        self._table_view.setSelectionMode(QTableView.SingleSelection)
        self._table_view.setAlternatingRowColors(True)
        self._table_view.setSortingEnabled(True)
        self._table_view.setEditTriggers(QTableView.NoEditTriggers)
        
        # 헤더 설정
        header = self._table_view.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # 타입
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # 그룹 ID
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # 파일 수
        header.setSectionResizeMode(3, QHeaderView.Stretch)  # 추천 Keeper
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # 신뢰도
        header.setSectionResizeMode(5, QHeaderView.Stretch)  # 작품명/제목
        
        # 기본 정렬: 신뢰도 내림차순
        self._table_view.sortByColumn(
            DuplicateGroupsTableModel.COL_CONFIDENCE,
            Qt.DescendingOrder
        )
        
        # 초기 상태: 빈 테이블
        group_layout.addWidget(self._table_view)
        layout.addWidget(group)
    
    def _connect_signals(self) -> None:
        """시그널 연결."""
        # 선택 변경 시 group_selected 시그널 발생
        self._table_view.selectionModel().selectionChanged.connect(
            self._on_selection_changed
        )
    
    def _on_selection_changed(self) -> None:
        """선택 변경 핸들러."""
        selected_indexes = self._table_view.selectionModel().selectedRows()
        if selected_indexes:
            # 첫 번째 선택된 행
            proxy_index = selected_indexes[0]
            source_index = self._proxy_model.mapToSource(proxy_index)
            result = self._model.get_result(source_index.row())
            if result:
                self.group_selected.emit(result.group_id)
        else:
            # 선택 해제
            self.group_selected.emit(-1)  # -1은 선택 해제를 의미
    
    def set_results(self, results: list) -> None:
        """결과 설정.
        
        Args:
            results: 중복 그룹 결과 리스트 (DuplicateGroupResult).
        """
        self._model.set_results(results)
    
    def clear_selection(self) -> None:
        """선택 해제."""
        self._table_view.clearSelection()
    
    def set_type_filter(self, type_str: Optional[str]) -> None:
        """타입 필터 설정.
        
        Args:
            type_str: 타입 문자열 (None이면 전체).
        """
        self._proxy_model.set_type_filter(type_str)
    
    def set_min_confidence(self, confidence: float) -> None:
        """최소 신뢰도 설정.
        
        Args:
            confidence: 최소 신뢰도 (0.0 ~ 1.0).
        """
        self._proxy_model.set_min_confidence(confidence)
    
    def set_search_text(self, text: str) -> None:
        """검색 텍스트 설정.
        
        Args:
            text: 검색 텍스트.
        """
        self._proxy_model.set_search_text(text)
