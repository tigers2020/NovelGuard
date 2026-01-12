"""파일 리스트 테이블 컴포넌트."""
import logging
import re
from datetime import datetime
from typing import Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QGroupBox,
    QHeaderView,
    QStyledItemDelegate,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from gui.models.file_data_store import FileData, FileDataStore

logger = logging.getLogger(__name__)


class DuplicateColumnsDelegate(QStyledItemDelegate):
    """중복 그룹(6), 대표(7) 컬럼을 FileData에서 직접 렌더링.
    
    setText() 호출 없이 paint 이벤트에서 FileData를 읽어 표시 문자열을 생성합니다.
    """
    
    # 파일명에서 타이틀 추출용 정규식 패턴
    _TITLE_EXTRACT_PATTERNS = [
        re.compile(r'\s+\d+\s*[-~]\s*\d+.*$'),  # " 1-176" 또는 " 1~176" 형식
        re.compile(r'\s+\d+[화권장회부].*$'),  # " 1화", " 1권" 등
        re.compile(r'\s+본편\s+\d+.*$'),  # " 본편 1-1213" 등
        re.compile(r'\s+외전\s+\d+.*$'),  # " 외전 1-71" 등
    ]
    
    def _extract_title_from_filename(self, filename: str) -> str:
        """파일명에서 소설 타이틀을 추출.
        
        Args:
            filename: 파일명 (확장자 포함 또는 제외).
            
        Returns:
            추출된 타이틀.
        """
        # 확장자 제거
        name = filename.rsplit('.', 1)[0] if '.' in filename else filename
        
        # 회차 범위 패턴 제거
        for pattern in self._TITLE_EXTRACT_PATTERNS:
            name = pattern.sub('', name)
        
        # 태그 패턴 제거 (예: "(완)", "[에필]", "@태그")
        name = re.sub(r'\([^)]*\)', '', name)  # (태그)
        name = re.sub(r'\[[^\]]*\]', '', name)  # [태그]
        name = re.sub(r'@[^\s]+', '', name)  # @태그
        
        # 양쪽 공백 제거
        title = name.strip()
        
        return title if title else filename  # 추출 실패 시 원본 반환
    
    def initStyleOption(self, option, index):
        """스타일 옵션 초기화. FileData에서 값을 읽어 표시 텍스트를 설정."""
        super().initStyleOption(option, index)

        table = self.parent()  # QTableWidget
        row = index.row()
        col = index.column()

        # FileData는 0번 컬럼 item의 UserRole에서 가져옴
        base_item = table.item(row, 0)
        if not base_item:
            return

        file_data = base_item.data(Qt.UserRole)
        if not isinstance(file_data, FileData):
            return

        if col == 6:  # 중복 그룹 컬럼
            group_text = "-"
            if file_data.duplicate_group_id is not None:
                # 파일명에서 타이틀 추출
                title = self._extract_title_from_filename(file_data.path.name)
                group_text = title
                if file_data.similarity_score is not None:
                    group_text += f" ({file_data.similarity_score:.0%})"
            option.text = group_text

        elif col == 7:  # 대표 파일 컬럼
            # 그룹이 없는 개인은 자체가 대표
            is_representative = file_data.is_canonical or file_data.duplicate_group_id is None
            option.text = "✓" if is_representative else "-"


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
        
        # 파일 추가용 배치 타이머
        self._batch_timer = QTimer(self)
        self._batch_timer.setSingleShot(True)
        self._batch_timer.timeout.connect(self._flush_pending_files)
        self._batch_timer.setInterval(50)  # 50ms마다 배치 처리
        
        # file_id -> row 인덱스 캐시
        self._row_by_file_id: dict[int, int] = {}
        
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
        
        # 컬럼 6, 7에 delegate 설정 (중복 그룹, 대표 파일)
        duplicate_delegate = DuplicateColumnsDelegate(self._table)
        self._table.setItemDelegateForColumn(6, duplicate_delegate)
        self._table.setItemDelegateForColumn(7, duplicate_delegate)
        
        # 헤더 클릭 핸들러 연결 (컬럼 6, 7 정렬 비활성화)
        header.sectionClicked.connect(self._on_header_clicked)
        
        group_layout.addWidget(self._table)
        layout.addWidget(group)
    
    def _connect_signals(self) -> None:
        """시그널 연결."""
        # 시그널 연결 전 로그 (log_sink가 있으면)
        # FileDataStore는 log_sink를 private으로 가지고 있지만, 시그널 연결 확인을 위해
        # 표준 logging 사용 (debug_step은 log_sink가 필요)
        
        self._data_store.file_added.connect(self._on_file_added)
        self._data_store.files_added_batch.connect(self._on_files_added_batch)
        self._data_store.file_updated.connect(self._on_file_updated)  # 단일 업데이트는 유지
        
        # files_updated_batch 시그널 연결
        connected = self._data_store.files_updated_batch.connect(self._on_files_updated_batch)  # 신규
        print(f"[DEBUG] FileListTableWidget._connect_signals: files_updated_batch connected={connected}")
        logger.debug("FileListTableWidget._connect_signals: files_updated_batch connected=%s", connected)
        
        self._data_store.files_cleared.connect(self._on_files_cleared)
        self._data_store.files_removed.connect(self._on_files_removed)
        # data_changed 연결 제거 - 전체 테이블 리프레시가 반복 호출되어 UI 프리징 발생
        # 개별 시그널(file_added, files_added_batch, file_updated, files_cleared, files_removed)로 충분히 처리 가능
    
    def _on_header_clicked(self, logical_index: int) -> None:
        """헤더 클릭 핸들러. 컬럼 6, 7은 정렬 비활성화.
        
        Args:
            logical_index: 클릭된 컬럼 인덱스.
        """
        if logical_index in (6, 7):
            return  # 정렬 금지
        # 다른 컬럼은 기본 정렬 동작 수행
        self._table.sortItems(logical_index, self._table.horizontalHeader().sortIndicatorOrder())
    
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
            # 인덱스 캐시 업데이트 (신규)
            self._row_by_file_id[file_data.file_id] = row
        
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
    
    def _on_files_updated_batch(self, file_ids: list[int]) -> None:
        """파일 업데이트 배치 핸들러 (단순화됨).
        
        Delegate 방식으로 전환하여 데이터만 갱신하고 viewport 업데이트 1회만 호출합니다.
        
        Args:
            file_ids: 업데이트된 파일 ID 리스트.
        """
        # 데이터는 이미 FileDataStore에서 갱신됨
        # 컬럼 6, 7은 Delegate가 paint에서 FileData를 직접 읽어 표시
        was_sorting = self._table.isSortingEnabled()
        if was_sorting:
            self._table.setSortingEnabled(False)
        
        self._table.viewport().update()  # ✅ repaint 트리거 1회
        
        if was_sorting:
            self._table.setSortingEnabled(True)
    
    def _on_files_cleared(self) -> None:
        """파일 삭제 핸들러."""
        self._table.setRowCount(0)
        # 인덱스 캐시 클리어 (신규)
        self._row_by_file_id.clear()
    
    def _on_files_removed(self, file_ids: list[int]) -> None:
        """파일 제거 핸들러.
        
        Args:
            file_ids: 제거된 파일 ID 리스트.
        """
        # 제거할 행들을 역순으로 정렬 (뒤에서부터 제거하여 인덱스 문제 방지)
        rows_to_remove: list[int] = []
        file_ids_to_remove = set(file_ids)
        
        for file_id in file_ids:
            row = self._row_by_file_id.get(file_id)
            if row is not None and 0 <= row < self._table.rowCount():
                # 중복 체크
                if row not in rows_to_remove:
                    rows_to_remove.append(row)
        
        # 역순으로 정렬하여 뒤에서부터 제거
        rows_to_remove.sort(reverse=True)
        
        # 행 제거
        for row in rows_to_remove:
            self._table.removeRow(row)
        
        # 인덱스 캐시에서 제거된 file_id 제거
        for file_id in file_ids_to_remove:
            self._row_by_file_id.pop(file_id, None)
        
        # 나머지 캐시는 행 제거로 인해 변경되었을 수 있지만,
        # 실제 사용 시 _find_row_by_file_id에서 재검증되므로 문제 없음
    
    def _refresh_table(self) -> None:
        """테이블 새로고침."""
        self._table.setRowCount(0)
        for file_data in self._data_store.get_all_files():
            self._add_file_row(file_data)
    
    def _find_row_by_file_id(self, file_id: int) -> int:
        """파일 ID로 행 찾기 (인덱스 캐시 사용).
        
        Args:
            file_id: 파일 ID.
        
        Returns:
            행 인덱스. 없으면 -1.
        """
        # 인덱스 캐시 사용 (O(1))
        row = self._row_by_file_id.get(file_id, -1)
        
        # 캐시에 없으면 선형 탐색 (fallback, 드물게 발생)
        if row == -1:
            for r in range(self._table.rowCount()):
                item = self._table.item(r, 0)
                if item:
                    data = item.data(Qt.UserRole)
                    if isinstance(data, FileData) and data.file_id == file_id:
                        # 캐시 업데이트
                        self._row_by_file_id[file_id] = r
                        return r
            return -1
        
        # 캐시에 있지만 행이 유효한지 확인 (정렬 등으로 인한 변경 대응)
        if 0 <= row < self._table.rowCount():
            item = self._table.item(row, 0)
            if item:
                data = item.data(Qt.UserRole)
                if isinstance(data, FileData) and data.file_id == file_id:
                    return row
        
        # 캐시 무효화 (행이 변경됨)
        self._row_by_file_id.pop(file_id, None)
        return -1
    
    def _add_file_row(self, file_data: FileData) -> None:
        """파일 행 추가.
        
        Args:
            file_data: 파일 데이터.
        """
        row = self._table.rowCount()
        self._table.insertRow(row)
        self._set_file_row_data(row, file_data)
        # 인덱스 캐시 업데이트 (신규)
        self._row_by_file_id[file_data.file_id] = row
    
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
        
        # 중복 그룹 (컬럼 6) - 빈 아이템만 생성 (delegate가 paint에서 표시)
        if not self._table.item(row, 6):
            group_item = QTableWidgetItem("")
            self._table.setItem(row, 6, group_item)
        
        # 대표 파일 (컬럼 7) - 빈 아이템만 생성 (delegate가 paint에서 표시)
        if not self._table.item(row, 7):
            canonical_item = QTableWidgetItem("")
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
