"""
중복 결과 업데이터 모듈

중복 검사 결과를 테이블에 업데이트하는 기능을 제공합니다.
"""

import time
from typing import Optional, Callable
from PySide6.QtWidgets import QTableWidget, QTableWidgetItem, QMessageBox
from PySide6.QtCore import Qt, QTimer, QSignalBlocker

from models.file_record import FileRecord
from analyzers.duplicate_group import DuplicateGroup
from utils.logger import get_logger
from utils.constants import DUPLICATE_UPDATE_BATCH_SIZE, UI_UPDATE_DELAY_MS


class DuplicateResultUpdater:
    """중복 결과 업데이터 클래스.
    
    중복 검사 결과를 테이블에 효율적으로 업데이트합니다.
    배치 업데이트와 상태 캐싱을 통해 UI 반응성을 유지합니다.
    
    Attributes:
        _logger: 로거 인스턴스
        _table: 업데이트할 테이블 위젯
        _state_cache: 중복 상태 캐시 (path -> (is_duplicate, group_num))
        _update_index: 현재 업데이트 인덱스
        _pending_updates: 대기 중인 업데이트 리스트
        _message_callback: 메시지박스 표시 콜백 함수
    """
    
    def __init__(
        self,
        table: QTableWidget,
        message_callback: Optional[Callable[[bool, int, int], None]] = None
    ) -> None:
        """DuplicateResultUpdater 초기화.
        
        Args:
            table: 업데이트할 테이블 위젯
            message_callback: 메시지박스 표시 콜백 함수
                (has_duplicates: bool, group_count: int, total_count: int) -> None
        """
        self._logger = get_logger("DuplicateResultUpdater")
        self._table = table
        self._message_callback = message_callback
        self._state_cache: dict[str, tuple[bool, int]] = {}
        self._update_index: int = 0
        self._pending_updates: list[tuple[int, str, bool, Optional[QTableWidgetItem]]] = []
    
    def clear_cache(self) -> None:
        """상태 캐시를 초기화합니다."""
        self._state_cache.clear()
    
    def update_results(
        self,
        duplicate_groups: list[list[FileRecord]],
        message_info: Optional[tuple[bool, int, int]] = None
    ) -> None:
        """중복 검사 결과를 테이블에 업데이트합니다.
        
        테이블 정렬 후에도 올바르게 작동하도록 path 기반으로 매칭합니다.
        대량 업데이트 시 UI 반응성을 위해 QTimer로 점진적 업데이트를 수행합니다.
        
        Args:
            duplicate_groups: 중복 그룹 리스트. 각 그룹은 FileRecord 리스트.
            message_info: 메시지박스 표시 정보 (has_duplicates, group_count, total_count)
        """
        start_time = time.time()
        
        self._logger.debug(f"중복 검사 결과 업데이트: {len(duplicate_groups)}개 그룹")
        
        # 파일 경로 → 그룹 번호 매핑 생성 (path 기반 비교로 안전성 확보)
        path_to_group: dict[str, int] = {}
        for group_idx, group in enumerate(duplicate_groups, start=1):
            for file_record in group:
                path_str = str(file_record.path)
                path_to_group[path_str] = group_idx
                self._logger.debug(f"그룹 {group_idx}: {path_str}")
        
        self._logger.debug(f"path_to_group 매핑: {len(path_to_group)}개 파일")
        
        # 테이블 아이템을 미리 캐싱 (성능 향상)
        # 한 번만 순회하여 모든 아이템을 가져옴
        row_count = self._table.rowCount()
        cached_items: list[tuple[Optional[QTableWidgetItem], Optional[QTableWidgetItem]]] = []
        for row in range(row_count):
            name_item = self._table.item(row, 0)
            duplicate_item = self._table.item(row, 3)
            cached_items.append((name_item, duplicate_item))
        
        # 업데이트할 항목 리스트 생성 (diff 방식: 변경된 행만 업데이트)
        # path 기반 캐시를 사용하여 이전 상태와 비교
        self._pending_updates = []
        changed_count = 0
        skipped_count = 0
        
        for row in range(row_count):
            name_item, duplicate_item = cached_items[row]
            if name_item is None:
                self._logger.debug(f"행 {row}: name_item이 None")
                continue
            
            file_path_str = name_item.data(Qt.ItemDataRole.UserRole)
            if not file_path_str:
                self._logger.debug(f"행 {row}: file_path_str이 없음")
                continue
            
            # 새로운 상태 계산
            new_is_dup = file_path_str in path_to_group
            new_group = path_to_group.get(file_path_str, 0)
            
            if new_is_dup:
                self._logger.debug(f"행 {row}: 중복 발견 - {file_path_str} (그룹 {new_group})")
            
            # 이전 상태와 비교 (캐시 사용)
            old_state = self._state_cache.get(file_path_str, (None, None))
            old_is_dup, old_group = old_state
            
            # 상태가 동일하면 스킵 (diff 적용)
            if old_state == (new_is_dup, new_group):
                skipped_count += 1
                continue
            
            # 상태가 변경되었으므로 캐시 업데이트 및 업데이트 리스트에 추가
            self._state_cache[file_path_str] = (new_is_dup, new_group)
            changed_count += 1
            
            if new_is_dup:
                new_text = f"중복 (그룹 {new_group})"
            else:
                # 정상은 "-"로 표시 (초기값과 동일, 업데이트 최소화)
                new_text = "-"
            
            self._pending_updates.append((row, new_text, new_is_dup, duplicate_item))
        
        self._logger.debug(
            f"중복 상태 diff: {changed_count}개 변경, {skipped_count}개 스킵 "
            f"(총 {row_count}개 중, path_to_group: {len(path_to_group)}개)"
        )
        
        # 업데이트할 항목이 없으면 종료
        if not self._pending_updates:
            self._logger.debug("업데이트할 항목이 없습니다.")
            # 메시지박스는 여전히 표시
            if message_info is not None and self._message_callback:
                has_duplicates, group_count, total_count = message_info
                self._message_callback(has_duplicates, group_count, total_count)
            return
        
        # QTimer로 점진적 업데이트 (배치 크기: DUPLICATE_UPDATE_BATCH_SIZE개씩, UI 반응성 향상)
        # 배치 크기를 줄여서 각 배치당 소요 시간을 줄이고 UI 프리징 최소화
        self._update_index = 0
        batch_size = DUPLICATE_UPDATE_BATCH_SIZE
        
        self._logger.debug(f"배치 업데이트 시작: {len(self._pending_updates)}개 항목")
        
        def update_batch() -> None:
            """배치 단위로 테이블 업데이트."""
            batch_start = time.time()
            
            end_idx = min(self._update_index + batch_size, len(self._pending_updates))
            
            # UI 업데이트 완전 차단 (성능 최적화)
            # 정렬, 시그널, 리사이즈, 페인팅 모두 비활성화
            was_sorting_enabled = self._table.isSortingEnabled()
            self._table.setSortingEnabled(False)
            
            # QSignalBlocker를 사용하여 시그널 차단 (RAII 패턴)
            signal_blocker = QSignalBlocker(self._table)
            self._table.setUpdatesEnabled(False)
            self._table.viewport().setUpdatesEnabled(False)
            
            try:
                for i in range(self._update_index, end_idx):
                    row, text, is_duplicate, duplicate_item = self._pending_updates[i]
                    
                    # 중복 여부 컬럼 (인덱스 3) - 캐시된 아이템 사용
                    if duplicate_item is None:
                        duplicate_item = QTableWidgetItem()
                        self._table.setItem(row, 3, duplicate_item)
                        # 캐시 업데이트
                        self._pending_updates[i] = (row, text, is_duplicate, duplicate_item)
                    
                    # 텍스트 업데이트 (변경된 경우만)
                    current_text = duplicate_item.text()
                    if current_text != text:
                        duplicate_item.setText(text)
                    
                    # 색상 업데이트 (setData 사용 + 변경된 경우만)
                    current_color = duplicate_item.data(Qt.ItemDataRole.ForegroundRole)
                    new_color = Qt.GlobalColor.red if is_duplicate else Qt.GlobalColor.black
                    
                    # 색상이 변경된 경우만 업데이트
                    if current_color != new_color:
                        duplicate_item.setData(Qt.ItemDataRole.ForegroundRole, new_color)
            finally:
                # QSignalBlocker는 자동으로 해제됨 (블록 종료 시)
                # UI 업데이트 재개 (원래 상태로 복원)
                self._table.viewport().setUpdatesEnabled(True)
                self._table.setUpdatesEnabled(True)
                if was_sorting_enabled:
                    self._table.setSortingEnabled(True)
                # 마지막에 한 번만 viewport 업데이트
                self._table.viewport().update()
            
            batch_elapsed = (time.time() - batch_start) * 1000
            self._update_index = end_idx
            
            # 더 업데이트할 항목이 있으면 다음 배치 예약
            if self._update_index < len(self._pending_updates):
                # UI_UPDATE_DELAY_MS 후 다음 배치 (이벤트 루프에 여유 제공)
                QTimer.singleShot(UI_UPDATE_DELAY_MS, update_batch)
            else:
                # 모든 업데이트 완료
                elapsed = (time.time() - start_time) * 1000
                self._pending_updates = []
                
                # 메시지박스 지연 표시 (업데이트 완료 후) - 프리징 체감 최소화
                if message_info is not None and self._message_callback:
                    has_duplicates, group_count, total_count = message_info
                    self._message_callback(has_duplicates, group_count, total_count)
        
        # 첫 배치 시작 (즉시 실행)
        update_batch()
    
    def update_results_with_groups(
        self,
        duplicate_groups: list[DuplicateGroup],
        message_info: Optional[tuple[bool, int, int]] = None
    ) -> None:
        """중복 검사 결과를 테이블에 업데이트합니다 (DuplicateGroup 정보 포함).
        
        keep_file은 "보관"으로, 나머지는 "중복"으로 표시하여 파일 정리와 일치시킵니다.
        테이블 정렬 후에도 올바르게 작동하도록 path 기반으로 매칭합니다.
        대량 업데이트 시 UI 반응성을 위해 QTimer로 점진적 업데이트를 수행합니다.
        
        Args:
            duplicate_groups: 중복 그룹 리스트 (keep_file 정보 포함)
            message_info: 메시지박스 표시 정보 (has_duplicates, group_count, total_count)
        """
        start_time = time.time()
        
        self._logger.debug(f"중복 검사 결과 업데이트 (그룹 정보 포함): {len(duplicate_groups)}개 그룹")
        
        # 파일 경로 → (그룹 번호, is_keep_file) 매핑 생성
        path_to_info: dict[str, tuple[int, bool]] = {}
        for group_idx, group in enumerate(duplicate_groups, start=1):
            for file_record in group.members:
                path_str = str(file_record.path)
                is_keep_file = (group.keep_file is not None and file_record == group.keep_file)
                path_to_info[path_str] = (group_idx, is_keep_file)
                self._logger.debug(f"그룹 {group_idx}: {path_str} (keep_file: {is_keep_file})")
        
        self._logger.debug(f"path_to_info 매핑: {len(path_to_info)}개 파일")
        
        # 테이블 아이템을 미리 캐싱 (성능 향상)
        row_count = self._table.rowCount()
        cached_items: list[tuple[Optional[QTableWidgetItem], Optional[QTableWidgetItem]]] = []
        for row in range(row_count):
            name_item = self._table.item(row, 0)
            duplicate_item = self._table.item(row, 3)
            cached_items.append((name_item, duplicate_item))
        
        # 업데이트할 항목 리스트 생성 (diff 방식: 변경된 행만 업데이트)
        self._pending_updates = []
        changed_count = 0
        skipped_count = 0
        
        for row in range(row_count):
            name_item, duplicate_item = cached_items[row]
            if name_item is None:
                self._logger.debug(f"행 {row}: name_item이 None")
                continue
            
            file_path_str = name_item.data(Qt.ItemDataRole.UserRole)
            if not file_path_str:
                self._logger.debug(f"행 {row}: file_path_str이 없음")
                continue
            
            # 새로운 상태 계산
            if file_path_str in path_to_info:
                group_num, is_keep_file = path_to_info[file_path_str]
                new_is_dup = not is_keep_file  # keep_file이 아니면 중복
                new_group = group_num
                new_text = f"보관 (그룹 {group_num})" if is_keep_file else f"중복 (그룹 {group_num})"
            else:
                new_is_dup = False
                new_group = 0
                new_text = "-"
            
            if file_path_str in path_to_info:
                self._logger.debug(f"행 {row}: {new_text} - {file_path_str}")
            
            # 이전 상태와 비교 (캐시 사용)
            old_state = self._state_cache.get(file_path_str, (None, None))
            old_is_dup, old_group = old_state
            
            # 상태가 동일하면 스킵 (diff 적용)
            if old_state == (new_is_dup, new_group):
                skipped_count += 1
                continue
            
            # 상태가 변경되었으므로 캐시 업데이트 및 업데이트 리스트에 추가
            self._state_cache[file_path_str] = (new_is_dup, new_group)
            changed_count += 1
            
            self._pending_updates.append((row, new_text, new_is_dup, duplicate_item))
        
        self._logger.debug(
            f"중복 상태 diff: {changed_count}개 변경, {skipped_count}개 스킵 "
            f"(총 {row_count}개 중, path_to_info: {len(path_to_info)}개)"
        )
        
        # 업데이트할 항목이 없으면 종료
        if not self._pending_updates:
            self._logger.debug("업데이트할 항목이 없습니다.")
            # 메시지박스는 여전히 표시
            if message_info is not None and self._message_callback:
                has_duplicates, group_count, total_count = message_info
                self._message_callback(has_duplicates, group_count, total_count)
            return
        
        # QTimer로 점진적 업데이트 (배치 크기: DUPLICATE_UPDATE_BATCH_SIZE개씩, UI 반응성 향상)
        self._update_index = 0
        batch_size = DUPLICATE_UPDATE_BATCH_SIZE
        
        self._logger.debug(f"배치 업데이트 시작: {len(self._pending_updates)}개 항목")
        
        def update_batch() -> None:
            """배치 단위로 테이블 업데이트."""
            batch_start = time.time()
            
            end_idx = min(self._update_index + batch_size, len(self._pending_updates))
            
            # UI 업데이트 완전 차단 (성능 최적화)
            was_sorting_enabled = self._table.isSortingEnabled()
            self._table.setSortingEnabled(False)
            
            # QSignalBlocker를 사용하여 시그널 차단 (RAII 패턴)
            signal_blocker = QSignalBlocker(self._table)
            self._table.setUpdatesEnabled(False)
            self._table.viewport().setUpdatesEnabled(False)
            
            try:
                for i in range(self._update_index, end_idx):
                    row, text, is_duplicate, duplicate_item = self._pending_updates[i]
                    
                    # 중복 여부 컬럼 (인덱스 3) - 캐시된 아이템 사용
                    if duplicate_item is None:
                        duplicate_item = QTableWidgetItem()
                        self._table.setItem(row, 3, duplicate_item)
                        # 캐시 업데이트
                        self._pending_updates[i] = (row, text, is_duplicate, duplicate_item)
                    
                    # 텍스트 업데이트 (변경된 경우만)
                    current_text = duplicate_item.text()
                    if current_text != text:
                        duplicate_item.setText(text)
                    
                    # 색상 업데이트 (setData 사용 + 변경된 경우만)
                    # keep_file은 파란색, 중복은 빨간색, 정상은 검은색
                    current_color = duplicate_item.data(Qt.ItemDataRole.ForegroundRole)
                    if "보관" in text:
                        new_color = Qt.GlobalColor.blue
                    elif is_duplicate:
                        new_color = Qt.GlobalColor.red
                    else:
                        new_color = Qt.GlobalColor.black
                    
                    # 색상이 변경된 경우만 업데이트
                    if current_color != new_color:
                        duplicate_item.setData(Qt.ItemDataRole.ForegroundRole, new_color)
            finally:
                # QSignalBlocker는 자동으로 해제됨 (블록 종료 시)
                # UI 업데이트 재개 (원래 상태로 복원)
                self._table.viewport().setUpdatesEnabled(True)
                self._table.setUpdatesEnabled(True)
                if was_sorting_enabled:
                    self._table.setSortingEnabled(True)
                # 마지막에 한 번만 viewport 업데이트
                self._table.viewport().update()
            
            batch_elapsed = (time.time() - batch_start) * 1000
            self._update_index = end_idx
            
            # 더 업데이트할 항목이 있으면 다음 배치 예약
            if self._update_index < len(self._pending_updates):
                # UI_UPDATE_DELAY_MS 후 다음 배치 (이벤트 루프에 여유 제공)
                QTimer.singleShot(UI_UPDATE_DELAY_MS, update_batch)
            else:
                # 모든 업데이트 완료
                elapsed = (time.time() - start_time) * 1000
                self._pending_updates = []
                
                # 메시지박스 지연 표시 (업데이트 완료 후) - 프리징 체감 최소화
                if message_info is not None and self._message_callback:
                    has_duplicates, group_count, total_count = message_info
                    self._message_callback(has_duplicates, group_count, total_count)
        
        # 첫 배치 시작 (즉시 실행)
        update_batch()

