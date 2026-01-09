"""ResultIndexManager - Store 기반 인덱싱."""

from typing import Optional
from gui.stores.result_store import ResultStore
from gui.view_models.file_row import FileRow
from domain.models.duplicate_group import DuplicateGroup
from domain.models.integrity_issue import IntegrityIssue
from common.logging import setup_logging

logger = setup_logging()


class ResultIndexManager:
    """결과 인덱스 관리자.
    
    Store 기반 인덱싱으로 필터링 성능 향상.
    """
    
    def __init__(self, store: ResultStore) -> None:
        """ResultIndexManager 초기화.
        
        Args:
            store: ResultStore
        """
        self.store = store
        self._by_group_id: dict[int, list[int]] = {}  # group_id -> file_id 리스트
        self._by_issue_severity: dict[str, set[int]] = {}  # severity -> file_id 집합
        self._by_action: dict[str, set[int]] = {}  # action -> file_id 집합
    
    def add_rows(self, rows: list[FileRow]) -> None:
        """행 추가로 인덱스 업데이트.
        
        Args:
            rows: 추가할 FileRow 리스트
        """
        for row in rows:
            # Group ID 인덱스
            if row.group_id is not None:
                if row.group_id not in self._by_group_id:
                    self._by_group_id[row.group_id] = []
                if row.file_id not in self._by_group_id[row.group_id]:
                    self._by_group_id[row.group_id].append(row.file_id)
            
            # Action 인덱스
            if row.planned_action:
                if row.planned_action not in self._by_action:
                    self._by_action[row.planned_action] = set()
                self._by_action[row.planned_action].add(row.file_id)
    
    def update_rows(self, rows: list[FileRow]) -> None:
        """행 업데이트로 인덱스 업데이트.
        
        Args:
            rows: 업데이트할 FileRow 리스트
        """
        # 기존 인덱스에서 제거 후 재추가
        for row in rows:
            self._remove_row_from_index(row.file_id)
        
        self.add_rows(rows)
    
    def update_groups(self, groups: list[DuplicateGroup]) -> None:
        """그룹 업데이트로 인덱스 업데이트.
        
        Args:
            groups: 추가할 DuplicateGroup 리스트
        """
        for group in groups:
            self._by_group_id[group.group_id] = group.member_ids.copy()
    
    def update_issues(self, issues: list[IntegrityIssue]) -> None:
        """이슈 업데이트로 인덱스 업데이트.
        
        Args:
            issues: 추가할 IntegrityIssue 리스트
        """
        for issue in issues:
            if issue.severity not in self._by_issue_severity:
                self._by_issue_severity[issue.severity] = set()
            self._by_issue_severity[issue.severity].add(issue.file_id)
    
    def _remove_row_from_index(self, file_id: int) -> None:
        """행을 인덱스에서 제거.
        
        Args:
            file_id: 파일 ID
        """
        # Group ID 인덱스에서 제거
        for group_id, file_ids in self._by_group_id.items():
            if file_id in file_ids:
                file_ids.remove(file_id)
        
        # Action 인덱스에서 제거
        for action, file_ids in self._by_action.items():
            file_ids.discard(file_id)
    
    def get_file_ids_by_group(self, group_id: int) -> list[int]:
        """그룹 ID로 파일 ID 리스트 조회.
        
        Args:
            group_id: 그룹 ID
        
        Returns:
            파일 ID 리스트
        """
        return self._by_group_id.get(group_id, []).copy()
    
    def get_file_ids_by_severity(self, severity: str) -> set[int]:
        """심각도로 파일 ID 집합 조회.
        
        Args:
            severity: 심각도
        
        Returns:
            파일 ID 집합
        """
        return self._by_issue_severity.get(severity, set()).copy()
    
    def get_file_ids_by_action(self, action: str) -> set[int]:
        """액션으로 파일 ID 집합 조회.
        
        Args:
            action: 액션
        
        Returns:
            파일 ID 집합
        """
        return self._by_action.get(action, set()).copy()
    
    def clear(self) -> None:
        """모든 인덱스 초기화."""
        self._by_group_id.clear()
        self._by_issue_severity.clear()
        self._by_action.clear()

