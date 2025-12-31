"""
무결성 결과 업데이터 모듈

무결성 검사 결과를 테이블에 업데이트하는 기능을 제공합니다.
"""

import time
from typing import Optional
from PySide6.QtWidgets import QTableWidget, QTableWidgetItem
from PySide6.QtCore import Qt, QTimer, QSignalBlocker

from checkers.integrity_checker import IntegrityIssue
from utils.logger import get_logger
from utils.constants import UI_UPDATE_DELAY_MS, DUPLICATE_UPDATE_BATCH_SIZE


class IntegrityResultUpdater:
    """무결성 검사 결과를 테이블에 효율적으로 업데이트합니다.
    
    배치 업데이트를 통해 UI 반응성을 유지합니다.
    
    Attributes:
        _logger: 로거 인스턴스
        _table: 업데이트할 테이블 위젯
        _update_index: 현재 업데이트 인덱스
        _pending_updates: 대기 중인 업데이트 리스트
    """
    
    def __init__(self, table: QTableWidget) -> None:
        """IntegrityResultUpdater 초기화.
        
        Args:
            table: 업데이트할 테이블 위젯
        """
        self._logger = get_logger("IntegrityResultUpdater")
        self._table = table
        self._update_index: int = 0
        self._pending_updates: list[tuple[int, str, Optional[QTableWidgetItem]]] = []  # (row, display_text, integrity_item)
        self._state_cache: dict[str, str] = {}  # path -> display_text 캐시
    
    def update_results(self, issues: list[IntegrityIssue]) -> None:
        """무결성 검사 결과를 테이블에 업데이트합니다.
        
        IntegrityIssue 리스트를 파일 경로별로 그룹화하고,
        각 파일에 대해 최악 severity 1개만 표시합니다.
        severity 우선순위: ERROR > WARN > INFO
        
        대량 업데이트 시 UI 반응성을 위해 QTimer로 점진적 업데이트를 수행합니다.
        
        Args:
            issues: 무결성 문제 리스트
        """
        start_time = time.time()
        
        self._logger.debug(f"무결성 검사 결과 업데이트: {len(issues)}개 문제")
        
        if not self._table:
            self._logger.warning("테이블이 초기화되지 않았습니다.")
            return
        
        # 파일 경로별로 이슈 그룹화
        path_to_issues: dict[str, list[IntegrityIssue]] = {}
        for issue in issues:
            path_str = str(issue.path)
            if path_str not in path_to_issues:
                path_to_issues[path_str] = []
            path_to_issues[path_str].append(issue)
        
        # severity 우선순위 매핑
        severity_priority = {"ERROR": 3, "WARN": 2, "INFO": 1}
        
        # 각 파일에 대해 최악 severity 이슈 선택
        path_to_worst_issue: dict[str, IntegrityIssue] = {}
        for path_str, file_issues in path_to_issues.items():
            worst_issue = max(
                file_issues,
                key=lambda issue: severity_priority.get(issue.severity, 0)
            )
            path_to_worst_issue[path_str] = worst_issue
        
        # 테이블 행을 미리 캐싱하고 업데이트할 항목 리스트 생성 (diff 방식)
        row_count = self._table.rowCount()
        integrity_column = 4  # "무결성 상태" 컬럼 인덱스
        
        # 테이블 아이템을 미리 캐싱 (성능 향상)
        cached_items: list[tuple[Optional[QTableWidgetItem], Optional[QTableWidgetItem]]] = []
        for row in range(row_count):
            name_item = self._table.item(row, 0)
            integrity_item = self._table.item(row, integrity_column)
            cached_items.append((name_item, integrity_item))
        
        # 업데이트할 항목 리스트 생성 (diff 방식: 변경된 행만 업데이트)
        self._pending_updates = []
        changed_count = 0
        skipped_count = 0
        
        for row in range(row_count):
            name_item, integrity_item = cached_items[row]
            if name_item is None:
                continue
            
            # UserRole에서 파일 경로 가져오기
            file_path_str = name_item.data(Qt.ItemDataRole.UserRole)
            if not file_path_str:
                continue
            
            # 새로운 상태 계산
            if file_path_str in path_to_worst_issue:
                issue = path_to_worst_issue[file_path_str]
                new_display_text = self._format_integrity_status(issue)
            else:
                # 이슈가 없는 경우 "정상" 표시
                current_text = integrity_item.text() if integrity_item else "-"
                if current_text == "-":
                    new_display_text = "정상"
                else:
                    # 이미 다른 값이 있으면 유지 (변경 없음)
                    new_display_text = current_text
            
            # 이전 상태와 비교 (캐시 사용)
            old_display_text = self._state_cache.get(file_path_str)
            
            # 상태가 동일하면 스킵 (diff 적용)
            if old_display_text == new_display_text:
                skipped_count += 1
                continue
            
            # 상태가 변경되었으므로 캐시 업데이트 및 업데이트 리스트에 추가
            self._state_cache[file_path_str] = new_display_text
            changed_count += 1
            
            # 캐시된 아이템도 함께 저장 (성능 향상)
            self._pending_updates.append((row, new_display_text, integrity_item))
        
        self._logger.debug(
            f"무결성 상태 diff: {changed_count}개 변경, {skipped_count}개 스킵 "
            f"(총 {row_count}개 중, 이슈: {len(path_to_worst_issue)}개)"
        )
        
        # 업데이트할 항목이 없으면 종료
        if not self._pending_updates:
            self._logger.debug("업데이트할 항목이 없습니다.")
            return
        
        self._logger.debug(f"배치 업데이트 시작: {len(self._pending_updates)}개 항목")
        
        # QTimer로 점진적 업데이트
        # 무결성 업데이트는 중복 업데이트보다 단순하므로 배치 크기를 더 크게 설정
        self._update_index = 0
        batch_size = DUPLICATE_UPDATE_BATCH_SIZE * 2  # 100개씩 처리
        
        def update_batch() -> None:
            """배치 단위로 테이블 업데이트."""
            batch_start = time.time()
            
            end_idx = min(self._update_index + batch_size, len(self._pending_updates))
            
            # UI 업데이트 완전 차단 (성능 최적화)
            was_sorting_enabled = self._table.isSortingEnabled()
            self._table.setSortingEnabled(False)
            
            signal_blocker = QSignalBlocker(self._table)
            self._table.setUpdatesEnabled(False)
            self._table.viewport().setUpdatesEnabled(False)
            
            try:
                for i in range(self._update_index, end_idx):
                    row, display_text, integrity_item = self._pending_updates[i]
                    
                    # 무결성 상태 컬럼 (인덱스 4) - 캐시된 아이템 사용
                    if integrity_item is None:
                        integrity_item = QTableWidgetItem(display_text)
                        self._table.setItem(row, integrity_column, integrity_item)
                        # 캐시 업데이트
                        self._pending_updates[i] = (row, display_text, integrity_item)
                    else:
                        # 텍스트가 변경된 경우만 업데이트
                        if integrity_item.text() != display_text:
                            integrity_item.setText(display_text)
            finally:
                # UI 업데이트 재개
                self._table.viewport().setUpdatesEnabled(True)
                self._table.setUpdatesEnabled(True)
                if was_sorting_enabled:
                    self._table.setSortingEnabled(True)
                self._table.viewport().update()
            
            batch_elapsed = (time.time() - batch_start) * 1000
            self._update_index = end_idx
            
            # 더 업데이트할 항목이 있으면 다음 배치 예약
            if self._update_index < len(self._pending_updates):
                QTimer.singleShot(UI_UPDATE_DELAY_MS, update_batch)
            else:
                # 모든 업데이트 완료
                elapsed = (time.time() - start_time) * 1000
                self._pending_updates = []
                self._logger.debug(f"무결성 상태 업데이트 완료: {len(path_to_worst_issue)}개 파일 ({elapsed:.1f}ms)")
        
        # 첫 배치 시작 (즉시 실행)
        update_batch()
    
    def _format_integrity_status(self, issue: IntegrityIssue) -> str:
        """IntegrityIssue를 사용자 표시용 문자열로 변환.
        
        Args:
            issue: IntegrityIssue 객체
        
        Returns:
            사용자 표시용 한국어 문자열
        """
        severity_prefix = {
            "ERROR": "오류",
            "WARN": "경고",
            "INFO": "정보"
        }.get(issue.severity, "알 수 없음")
        
        # code에 따른 메시지 커스터마이징
        if issue.code == "EMPTY_FILE":
            return f"{severity_prefix}: 빈 파일"
        elif issue.code == "READ_ERROR":
            return f"{severity_prefix}: 파일 읽기 실패"
        elif issue.code == "DECODE_ERROR":
            encoding = issue.meta.get("encoding", "알 수 없음")
            return f"{severity_prefix}: 디코딩 실패 ({encoding})"
        else:
            # 기본적으로 issue.message 사용
            return f"{severity_prefix}: {issue.message}"

