"""ResultStore - Single Source of Truth."""

from typing import Optional
from threading import Lock
from gui.view_models.file_row import FileRow
from domain.models.duplicate_group import DuplicateGroup
from domain.models.integrity_issue import IntegrityIssue
from domain.models.action_plan import ActionPlan
from common.logging import setup_logging

logger = setup_logging()


class ResultStore:
    """UI 상태의 중앙 저장소 (Single Source of Truth).
    
    스레드 안전성을 보장하는 상태 저장소.
    """
    
    def __init__(self) -> None:
        """ResultStore 초기화."""
        self._lock = Lock()
        self._rows_by_id: dict[int, FileRow] = {}
        self._groups_by_id: dict[int, DuplicateGroup] = {}
        self._issues_by_file_id: dict[int, list[IntegrityIssue]] = {}
        self._plan: Optional[ActionPlan] = None
    
    @property
    def rows_by_id(self) -> dict[int, FileRow]:
        """파일 ID -> FileRow 매핑 (읽기 전용 복사)."""
        with self._lock:
            return self._rows_by_id.copy()
    
    @property
    def groups_by_id(self) -> dict[int, DuplicateGroup]:
        """그룹 ID -> DuplicateGroup 매핑 (읽기 전용 복사)."""
        with self._lock:
            return self._groups_by_id.copy()
    
    @property
    def issues_by_file_id(self) -> dict[int, list[IntegrityIssue]]:
        """파일 ID -> IntegrityIssue 리스트 매핑 (읽기 전용 복사)."""
        with self._lock:
            return {k: v.copy() for k, v in self._issues_by_file_id.items()}
    
    @property
    def plan(self) -> Optional[ActionPlan]:
        """ActionPlan."""
        with self._lock:
            return self._plan
    
    def add_rows(self, rows: list[FileRow]) -> None:
        """FileRow 추가.
        
        Args:
            rows: 추가할 FileRow 리스트
        """
        with self._lock:
            for row in rows:
                self._rows_by_id[row.file_id] = row
    
    def update_rows(self, rows: list[FileRow]) -> None:
        """FileRow 업데이트.
        
        Args:
            rows: 업데이트할 FileRow 리스트
        """
        with self._lock:
            for row in rows:
                if row.file_id in self._rows_by_id:
                    self._rows_by_id[row.file_id] = row
    
    def add_groups(self, groups: list[DuplicateGroup]) -> None:
        """DuplicateGroup 추가.
        
        Args:
            groups: 추가할 DuplicateGroup 리스트
        """
        with self._lock:
            for group in groups:
                self._groups_by_id[group.group_id] = group
    
    def add_issues(self, issues: list[IntegrityIssue]) -> None:
        """IntegrityIssue 추가.
        
        Args:
            issues: 추가할 IntegrityIssue 리스트
        """
        with self._lock:
            for issue in issues:
                if issue.file_id not in self._issues_by_file_id:
                    self._issues_by_file_id[issue.file_id] = []
                self._issues_by_file_id[issue.file_id].append(issue)
    
    def set_plan(self, plan: ActionPlan) -> None:
        """ActionPlan 설정.
        
        Args:
            plan: ActionPlan
        """
        with self._lock:
            self._plan = plan
    
    def get_row(self, file_id: int) -> Optional[FileRow]:
        """FileRow 조회.
        
        Args:
            file_id: 파일 ID
        
        Returns:
            FileRow 또는 None
        """
        with self._lock:
            return self._rows_by_id.get(file_id)
    
    def clear(self) -> None:
        """모든 데이터 삭제."""
        with self._lock:
            self._rows_by_id.clear()
            self._groups_by_id.clear()
            self._issues_by_file_id.clear()
            self._plan = None

