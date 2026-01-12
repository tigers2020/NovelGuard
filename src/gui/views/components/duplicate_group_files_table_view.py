"""중복 그룹 파일 테이블 뷰 컴포넌트."""
from typing import Optional, TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QGroupBox,
    QHeaderView,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from gui.models.duplicate_group_files_table_model import DuplicateGroupFilesTableModel

if TYPE_CHECKING:
    from gui.models.file_data_store import FileDataStore


class DuplicateGroupFilesTableView(QWidget):
    """중복 그룹 파일 테이블 뷰 위젯."""
    
    def __init__(self, parent: Optional[QWidget] = None, file_data_store: "FileDataStore" = None) -> None:
        """중복 그룹 파일 테이블 뷰 초기화.
        
        Args:
            parent: 부모 위젯.
            file_data_store: 파일 데이터 저장소 (필수).
        """
        super().__init__(parent)
        if file_data_store is None:
            raise ValueError("file_data_store is required")
        
        # 모델 생성
        self._model = DuplicateGroupFilesTableModel(self, file_data_store=file_data_store)
        
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """UI 설정."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 그룹 박스
        group = QGroupBox("그룹 파일 목록")
        group.setObjectName("settingsGroup")
        
        group_layout = QVBoxLayout(group)
        group_layout.setContentsMargins(0, 0, 0, 0)
        group_layout.setSpacing(0)
        
        # 테이블 뷰 생성
        self._table_view = QTableView()
        self._table_view.setModel(self._model)
        
        # 테이블 설정
        self._table_view.setSelectionBehavior(QTableView.SelectRows)
        self._table_view.setSelectionMode(QTableView.ExtendedSelection)  # 복수 선택 가능
        self._table_view.setAlternatingRowColors(True)
        self._table_view.setSortingEnabled(True)
        self._table_view.setEditTriggers(QTableView.NoEditTriggers)
        
        # 헤더 설정
        header = self._table_view.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # Keeper
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # 파일명
        header.setSectionResizeMode(2, QHeaderView.Stretch)  # 경로
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # 범위
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # 크기
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)  # 수정일
        
        # 기본 정렬: 파일명 기준
        self._table_view.sortByColumn(
            DuplicateGroupFilesTableModel.COL_NAME,
            Qt.AscendingOrder
        )
        
        # 초기 상태: 빈 테이블
        group_layout.addWidget(self._table_view)
        layout.addWidget(group)
    
    def set_group(self, result) -> None:
        """그룹 설정.
        
        Args:
            result: 중복 그룹 결과 (DuplicateGroupResult).
        """
        self._model.set_group(result)
    
    def clear(self) -> None:
        """테이블 초기화."""
        self._model.clear()
