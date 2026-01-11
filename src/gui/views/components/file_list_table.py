"""파일 리스트 테이블 컴포넌트."""
from datetime import datetime
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QGroupBox,
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from gui.models.file_data_store import FileData, FileDataStore


class FileListTableWidget(QWidget):
    """파일 리스트 테이블 위젯."""
    
    def __init__(self, data_store: FileDataStore, parent: Optional[QWidget] = None) -> None:
        """파일 리스트 테이블 초기화.
        
        Args:
            data_store: 파일 데이터 저장소.
            parent: 부모 위젯.
        """
        super().__init__(parent)
        self._data_store = data_store
        
        # 배치 처리 큐
        self._pending_files: list = []
        
        # 배치 업데이트 타이머
        self._batch_timer = QTimer(self)
        self._batch_timer.setSingleShot(True)
        self._batch_timer.timeout.connect(self._flush_pending_files)
        self._batch_timer.setInterval(50)  # 50ms마다 배치 처리
        
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self) -> None:
        """UI 설정."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 그룹 박스
        group = QGroupBox("파일 목록")
        group.setObjectName("settingsGroup")
        
        group_layout = QVBoxLayout(group)
        group_layout.setContentsMargins(0, 0, 0, 0)
        group_layout.setSpacing(0)
        
        # 테이블 생성
        self._table = QTableWidget()
        self._table.setColumnCount(10)
        self._table.setHorizontalHeaderLabels([
            "파일명",
            "경로",
            "크기",
            "수정일",
            "확장자",
            "인코딩",
            "중복 그룹",
            "대표 파일",
            "무결성",
            "속성"
        ])
        
        # 테이블 설정
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        self._table.setSelectionMode(QTableWidget.SingleSelection)
        self._table.setAlternatingRowColors(True)
        self._table.setSortingEnabled(True)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        
        # 헤더 설정
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # 파일명
        header.setSectionResizeMode(1, QHeaderView.Stretch)  # 경로
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # 크기
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # 수정일
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # 확장자
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)  # 인코딩
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)  # 중복 그룹
        header.setSectionResizeMode(7, QHeaderView.ResizeToContents)  # 대표 파일
        header.setSectionResizeMode(8, QHeaderView.ResizeToContents)  # 무결성
        header.setSectionResizeMode(9, QHeaderView.ResizeToContents)  # 속성
        
        # 초기 상태: 빈 테이블
        self._table.setRowCount(0)
        
        group_layout.addWidget(self._table)
        layout.addWidget(group)
    
    def _connect_signals(self) -> None:
        """시그널 연결."""
        self._data_store.file_added.connect(self._on_file_added)
        self._data_store.files_added_batch.connect(self._on_files_added_batch)
        self._data_store.file_updated.connect(self._on_file_updated)
        self._data_store.files_cleared.connect(self._on_files_cleared)
        self._data_store.data_changed.connect(self._refresh_table)
    
    def _on_file_added(self, file_data: FileData) -> None:
        """파일 추가 핸들러 (단일 파일)."""
        self._add_file_row(file_data)
    
    def _on_files_added_batch(self, file_data_list: list) -> None:
        """파일 추가 핸들러 (배치).
        
        Args:
            file_data_list: FileData 리스트.
        """
        # 배치 큐에 추가
        self._pending_files.extend(file_data_list)
        
        # 타이머 시작 (이미 실행 중이면 재시작)
        if not self._batch_timer.isActive():
            self._batch_timer.start()
    
    def _flush_pending_files(self) -> None:
        """대기 중인 파일들을 테이블에 추가."""
        if not self._pending_files:
            return
        
        # 정렬 비활성화 (성능 향상)
        was_sorting_enabled = self._table.isSortingEnabled()
        self._table.setSortingEnabled(False)
        
        # 배치로 행 추가
        current_row = self._table.rowCount()
        self._table.setRowCount(current_row + len(self._pending_files))
        
        for idx, file_data in enumerate(self._pending_files):
            row = current_row + idx
            self._set_file_row_data(row, file_data)
        
        # 정렬 재활성화
        self._table.setSortingEnabled(was_sorting_enabled)
        
        # 큐 비우기
        self._pending_files.clear()
    
    def _on_file_updated(self, file_data: FileData) -> None:
        """파일 업데이트 핸들러."""
        # 기존 행 찾기
        row = self._find_row_by_file_id(file_data.file_id)
        if row >= 0:
            self._update_file_row(row, file_data)
        else:
            # 없으면 추가
            self._add_file_row(file_data)
    
    def _on_files_cleared(self) -> None:
        """파일 삭제 핸들러."""
        self._table.setRowCount(0)
    
    def _refresh_table(self) -> None:
        """테이블 새로고침."""
        self._table.setRowCount(0)
        for file_data in self._data_store.get_all_files():
            self._add_file_row(file_data)
    
    def _find_row_by_file_id(self, file_id: int) -> int:
        """파일 ID로 행 찾기.
        
        Args:
            file_id: 파일 ID.
        
        Returns:
            행 인덱스. 없으면 -1.
        """
        for row in range(self._table.rowCount()):
            item = self._table.item(row, 0)
            if item:
                data = item.data(Qt.UserRole)
                if isinstance(data, FileData) and data.file_id == file_id:
                    return row
        return -1
    
    def _add_file_row(self, file_data: FileData) -> None:
        """파일 행 추가.
        
        Args:
            file_data: 파일 데이터.
        """
        row = self._table.rowCount()
        self._table.insertRow(row)
        self._set_file_row_data(row, file_data)
    
    def _update_file_row(self, row: int, file_data: FileData) -> None:
        """파일 행 업데이트.
        
        Args:
            row: 행 인덱스.
            file_data: 파일 데이터.
        """
        self._set_file_row_data(row, file_data)
    
    def _set_file_row_data(self, row: int, file_data: FileData) -> None:
        """파일 행 데이터 설정.
        
        Args:
            row: 행 인덱스.
            file_data: 파일 데이터.
        """
        scan_folder = self._data_store.scan_folder
        
        # 파일명
        name_item = QTableWidgetItem(file_data.path.name)
        name_item.setData(Qt.UserRole, file_data)  # 원본 데이터 저장
        self._table.setItem(row, 0, name_item)
        
        # 경로 (상대 경로로 표시)
        if scan_folder:
            try:
                rel_path = file_data.path.relative_to(scan_folder)
                path_str = str(rel_path)
            except ValueError:
                path_str = str(file_data.path)
        else:
            path_str = str(file_data.path)
        path_item = QTableWidgetItem(path_str)
        self._table.setItem(row, 1, path_item)
        
        # 크기
        size_item = QTableWidgetItem(self._format_file_size(file_data.size))
        size_item.setData(Qt.UserRole, file_data.size)  # 정렬을 위한 원본 값
        self._table.setItem(row, 2, size_item)
        
        # 수정일
        mtime_item = QTableWidgetItem(self._format_datetime(file_data.mtime))
        mtime_timestamp = file_data.mtime.timestamp()
        mtime_item.setData(Qt.UserRole, mtime_timestamp)
        self._table.setItem(row, 3, mtime_item)
        
        # 확장자
        ext_item = QTableWidgetItem(file_data.extension if file_data.extension else "-")
        self._table.setItem(row, 4, ext_item)
        
        # 인코딩
        encoding_text = "-"
        if file_data.encoding:
            if file_data.encoding_confidence:
                encoding_text = f"{file_data.encoding} ({file_data.encoding_confidence:.0%})"
            else:
                encoding_text = file_data.encoding
        encoding_item = QTableWidgetItem(encoding_text)
        self._table.setItem(row, 5, encoding_item)
        
        # 중복 그룹
        group_text = "-"
        if file_data.duplicate_group_id is not None:
            group_text = f"그룹 {file_data.duplicate_group_id}"
            if file_data.similarity_score is not None:
                group_text += f" ({file_data.similarity_score:.0%})"
        group_item = QTableWidgetItem(group_text)
        self._table.setItem(row, 6, group_item)
        
        # 대표 파일
        canonical_text = "✓" if file_data.is_canonical else "-"
        canonical_item = QTableWidgetItem(canonical_text)
        self._table.setItem(row, 7, canonical_item)
        
        # 무결성
        integrity_text = "-"
        if file_data.integrity_severity:
            severity_icon = {
                "ERROR": "🔴",
                "WARN": "🟡",
                "INFO": "🔵"
            }.get(file_data.integrity_severity, "")
            issue_count = len(file_data.integrity_issues)
            if issue_count > 0:
                integrity_text = f"{severity_icon} {issue_count}개"
        integrity_item = QTableWidgetItem(integrity_text)
        self._table.setItem(row, 8, integrity_item)
        
        # 속성
        attrs = []
        if file_data.entry.is_symlink:
            attrs.append("링크")
        if file_data.entry.is_hidden:
            attrs.append("숨김")
        attr_text = ", ".join(attrs) if attrs else "-"
        attr_item = QTableWidgetItem(attr_text)
        self._table.setItem(row, 9, attr_item)
    
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
        
        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024
            unit_index += 1
        
        if unit_index == 0:
            return f"{int(size)} {units[unit_index]}"
        else:
            return f"{size:.2f} {units[unit_index]}"
    
    def _format_datetime(self, dt: datetime) -> str:
        """날짜/시간을 문자열로 변환.
        
        Args:
            dt: datetime 객체.
        
        Returns:
            포맷된 날짜/시간 문자열 (예: "2024-01-01 12:00:00").
        """
        return dt.strftime("%Y-%m-%d %H:%M:%S")
