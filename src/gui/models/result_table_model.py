"""결과 테이블 모델 구현.

QAbstractTableModel을 상속하여 결과 데이터를 테이블 형태로 표시.
Store 기반 읽기, file_id 인덱스 지원.
"""

# 표준 라이브러리
from typing import Any, Optional

# 서드파티
from PySide6.QtCore import QAbstractTableModel, Qt, QModelIndex
from PySide6.QtGui import QColor

# 로컬
from gui.stores.result_store import ResultStore
from gui.view_models.file_row import FileRow


class ResultTableModel(QAbstractTableModel):
    """결과 테이블 모델 클래스.
    
    중복 파일, 작은 파일, 무결성 문제 등의 결과를 테이블 형태로 표시.
    Store 기반 읽기, file_id 인덱스 지원.
    """
    
    # 컬럼 정의
    COLUMN_STATUS = 0
    COLUMN_GROUP_ID = 1
    COLUMN_GROUP_TYPE = 2
    COLUMN_CANONICAL = 3
    COLUMN_SIMILARITY = 4
    COLUMN_SIZE = 5
    COLUMN_ENCODING = 6
    COLUMN_ISSUES = 7
    COLUMN_ACTION = 8
    COLUMN_PATH = 9
    
    COLUMN_NAMES = [
        "상태",
        "GroupID",
        "유형",
        "보존본",
        "유사도",
        "크기",
        "인코딩",
        "이슈",
        "예정 조치",
        "경로",
    ]
    
    # Qt.UserRole + n (정렬용 원시값)
    ROLE_SIZE = Qt.ItemDataRole.UserRole + 1
    ROLE_MTIME = Qt.ItemDataRole.UserRole + 2
    ROLE_SIMILARITY = Qt.ItemDataRole.UserRole + 3
    
    def __init__(self, store: ResultStore, parent=None) -> None:
        """모델 초기화.
        
        Args:
            store: ResultStore
            parent: 부모 객체
        """
        super().__init__(parent)
        self.store = store
        self._rows: list[FileRow] = []
        self._file_id_to_index: dict[int, int] = {}  # file_id -> row_index
    
    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """행 개수 반환.
        
        Args:
            parent: 부모 인덱스
            
        Returns:
            행 개수
        """
        return len(self._rows)
    
    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """컬럼 개수 반환.
        
        Args:
            parent: 부모 인덱스
            
        Returns:
            컬럼 개수
        """
        return len(self.COLUMN_NAMES)
    
    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole
    ) -> Optional[str]:
        """헤더 데이터 반환.
        
        Args:
            section: 섹션 인덱스
            orientation: 방향 (가로/세로)
            role: 데이터 역할
            
        Returns:
            헤더 텍스트
        """
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            if 0 <= section < len(self.COLUMN_NAMES):
                return self.COLUMN_NAMES[section]
        return None
    
    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        """셀 데이터 반환 (O(1)).
        
        Args:
            index: 인덱스
            role: 데이터 역할
            
        Returns:
            셀 데이터
        """
        if not index.isValid() or index.row() >= len(self._rows):
            return None
        
        row = self._rows[index.row()]
        column = index.column()
        
        if role == Qt.ItemDataRole.DisplayRole:
            # 컬럼별 데이터 반환
            if column == self.COLUMN_STATUS:
                return row.action_status
            elif column == self.COLUMN_GROUP_ID:
                return str(row.group_id) if row.group_id is not None else ""
            elif column == self.COLUMN_GROUP_TYPE:
                return row.group_type or ""
            elif column == self.COLUMN_CANONICAL:
                return "✓" if row.canonical else ""
            elif column == self.COLUMN_SIMILARITY:
                return f"{row.similarity:.1f}%" if row.similarity is not None else ""
            elif column == self.COLUMN_SIZE:
                return self._format_size(row.size)
            elif column == self.COLUMN_ENCODING:
                return row.encoding or ""
            elif column == self.COLUMN_ISSUES:
                return str(row.issues_count) if row.issues_count > 0 else ""
            elif column == self.COLUMN_ACTION:
                return row.planned_action or ""
            elif column == self.COLUMN_PATH:
                return row.short_path
        
        elif role == Qt.ItemDataRole.TextAlignmentRole:
            # 숫자 컬럼은 우측 정렬
            if column in [self.COLUMN_SIMILARITY, self.COLUMN_SIZE, self.COLUMN_ISSUES]:
                return Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            return Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        
        elif role == Qt.ItemDataRole.ToolTipRole:
            # 짧은 툴팁만 제공 (상세는 Repository에서 조회)
            return f"File ID: {row.file_id}\n경로: {row.short_path}"
        
        # 정렬용 원시값 (UserRole + n)
        elif role == self.ROLE_SIZE:
            return row.size
        elif role == self.ROLE_MTIME:
            return row.mtime
        elif role == self.ROLE_SIMILARITY:
            return row.similarity if row.similarity is not None else 0.0
        
        return None
    
    def appendRows(self, rows: list[FileRow]) -> None:
        """행 추가 (chunk 단위).
        
        Args:
            rows: 추가할 FileRow 리스트
        """
        if not rows:
            return
        
        start_row = len(self._rows)
        end_row = start_row + len(rows) - 1
        
        self.beginInsertRows(QModelIndex(), start_row, end_row)
        
        for row in rows:
            self._rows.append(row)
            self._file_id_to_index[row.file_id] = len(self._rows) - 1
        
        self.endInsertRows()
    
    def updateRows(self, rows: list[FileRow]) -> None:
        """행 업데이트 (file_id 기준 upsert).
        
        Args:
            rows: 업데이트할 FileRow 리스트
        """
        if not rows:
            return
        
        updated_indices = set()
        
        for row in rows:
            if row.file_id in self._file_id_to_index:
                # 기존 행 업데이트
                index = self._file_id_to_index[row.file_id]
                self._rows[index] = row
                updated_indices.add(index)
            else:
                # 새 행 추가
                self.appendRows([row])
                updated_indices.add(len(self._rows) - 1)
        
        # dataChanged 시그널 emit (범위 최소화)
        if updated_indices:
            min_index = min(updated_indices)
            max_index = max(updated_indices)
            top_left = self.index(min_index, 0)
            bottom_right = self.index(max_index, self.columnCount() - 1)
            self.dataChanged.emit(top_left, bottom_right, [])
    
    def getRowByFileId(self, file_id: int) -> Optional[FileRow]:
        """file_id로 행 조회 (O(1)).
        
        Args:
            file_id: 파일 ID
        
        Returns:
            FileRow 또는 None
        """
        index = self._file_id_to_index.get(file_id)
        if index is not None and 0 <= index < len(self._rows):
            return self._rows[index]
        return None
    
    def _format_size(self, size: int) -> str:
        """크기 포맷팅.
        
        Args:
            size: 크기 (bytes)
        
        Returns:
            포맷된 크기 문자열
        """
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        elif size < 1024 * 1024 * 1024:
            return f"{size / (1024 * 1024):.1f} MB"
        else:
            return f"{size / (1024 * 1024 * 1024):.1f} GB"
    
    def clear(self) -> None:
        """모든 데이터 제거."""
        self.beginResetModel()
        self._rows.clear()
        self._file_id_to_index.clear()
        self.endResetModel()
