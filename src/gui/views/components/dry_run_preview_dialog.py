"""Dry Run 미리보기 다이얼로그."""
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from application.use_cases.move_duplicate_files import MoveOperation


class DryRunPreviewDialog(QDialog):
    """Dry Run 미리보기 다이얼로그.
    
    이동할 파일 목록을 테이블로 표시합니다.
    """
    
    def __init__(
        self,
        operations: list[MoveOperation],
        scan_folder: Path,
        parent: Optional[QWidget] = None
    ) -> None:
        """Dry Run 미리보기 다이얼로그 초기화.
        
        Args:
            operations: 이동 작업 목록.
            scan_folder: 스캔 폴더 경로.
            parent: 부모 위젯.
        """
        super().__init__(parent)
        self._operations = operations
        self._scan_folder = scan_folder
        
        self.setWindowTitle("Dry Run - 이동할 파일 미리보기")
        self.setMinimumSize(800, 600)
        
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """UI 설정."""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        
        # 정보 라벨
        info_label = QLabel(
            f"총 {len(self._operations)}개 파일이 duplicate/ 폴더로 이동됩니다."
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # 테이블 생성
        table = QTableWidget()
        table.setColumnCount(4)
        table.setHorizontalHeaderLabels([
            "원본 경로",
            "이동할 경로",
            "크기",
            "그룹 ID"
        ])
        
        # 테이블 설정
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setSelectionMode(QTableWidget.SingleSelection)
        table.setAlternatingRowColors(True)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSortingEnabled(True)
        
        # 헤더 설정
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)  # 원본 경로
        header.setSectionResizeMode(1, QHeaderView.Stretch)  # 이동할 경로
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # 크기
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # 그룹 ID
        
        # 데이터 채우기
        table.setRowCount(len(self._operations))
        for row, operation in enumerate(self._operations):
            # 원본 경로
            try:
                source_path_str = str(operation.source_path.relative_to(self._scan_folder))
            except ValueError:
                source_path_str = str(operation.source_path)
            source_item = QTableWidgetItem(source_path_str)
            table.setItem(row, 0, source_item)
            
            # 이동할 경로
            try:
                target_path_str = str(operation.target_path.relative_to(self._scan_folder))
            except ValueError:
                target_path_str = str(operation.target_path)
            target_item = QTableWidgetItem(target_path_str)
            table.setItem(row, 1, target_item)
            
            # 크기
            try:
                size_bytes = operation.source_path.stat().st_size
                size_text = self._format_file_size(size_bytes)
                size_item = QTableWidgetItem(size_text)
                size_item.setData(Qt.UserRole, size_bytes)  # 정렬을 위한 원본 값
            except Exception:
                size_item = QTableWidgetItem("-")
                size_item.setData(Qt.UserRole, 0)
            table.setItem(row, 2, size_item)
            
            # 그룹 ID
            group_text = str(operation.duplicate_group_id) if operation.duplicate_group_id is not None else "-"
            group_item = QTableWidgetItem(group_text)
            table.setItem(row, 3, group_item)
        
        layout.addWidget(table)
        
        # 버튼 박스
        button_box = QDialogButtonBox(QDialogButtonBox.Ok)
        button_box.accepted.connect(self.accept)
        layout.addWidget(button_box)
    
    def _format_file_size(self, size_bytes: int) -> str:
        """파일 크기를 사람이 읽기 쉬운 형식으로 변환.
        
        Args:
            size_bytes: 파일 크기 (바이트).
        
        Returns:
            포맷된 크기 문자열 (예: "1.5 KB", "2.3 MB").
        """
        if size_bytes == 0:
            return "0 B"
        
        units = ["B", "KB", "MB", "GB", "TB"]
        unit_index = 0
        size = float(size_bytes)
        
        from app.settings.constants import Constants
        while size >= Constants.BYTES_PER_KB and unit_index < len(units) - 1:
            size /= Constants.BYTES_PER_KB
            unit_index += 1
        
        if unit_index == 0:
            return f"{int(size)} {units[unit_index]}"
        else:
            return f"{size:.2f} {units[unit_index]}"
