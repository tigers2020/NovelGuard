"""액션 플랜 생성 유스케이스."""

from typing import Callable, Optional
from infra.db.file_repository import FileRepository
from domain.models.action_plan import ActionPlan, ActionItem
from domain.models.duplicate_group import DuplicateGroup
from domain.models.integrity_issue import IntegrityIssue
from domain.models.file_record import FileRecord
from domain.services.canonical_selector import CanonicalSelector
from common.logging import setup_logging

logger = setup_logging()


def _should_delete_duplicate(record: FileRecord, is_canonical: bool = False) -> bool:
    """중복 파일 삭제 여부 판정 (v1 내부 함수, v1.5에서 CleanupPolicy로 분리 예정).
    
    Args:
        record: 파일 레코드
        is_canonical: canonical 파일 여부
    
    Returns:
        삭제 여부 (canonical이 아니면 삭제)
    """
    return not is_canonical


def _should_delete_small_file(record: FileRecord, min_size_bytes: int = 1024) -> bool:
    """작은 파일 삭제 여부 판정 (v1 내부 함수, v1.5에서 CleanupPolicy로 분리 예정).
    
    Args:
        record: 파일 레코드
        min_size_bytes: 최소 크기 (bytes)
    
    Returns:
        삭제 여부
    """
    return record.size < min_size_bytes


def _should_convert_encoding(record: FileRecord, target_encoding: str = "UTF-8") -> bool:
    """인코딩 변환 여부 판정 (v1 내부 함수, v1.5에서 CleanupPolicy로 분리 예정).
    
    Args:
        record: 파일 레코드
        target_encoding: 대상 인코딩
    
    Returns:
        변환 여부
    """
    if not record.is_text:
        return False
    
    if not record.encoding_detected:
        return False
    
    return record.encoding_detected.upper() != target_encoding.upper()


class BuildActionPlanUseCase:
    """액션 플랜 생성 유스케이스."""
    
    def __init__(
        self,
        repository: FileRepository,
        selector: Optional[CanonicalSelector] = None
    ) -> None:
        """유스케이스 초기화.
        
        Args:
            repository: FileRepository
            selector: CanonicalSelector (None이면 기본값)
        """
        self.repository = repository
        self.selector = selector or CanonicalSelector()
    
    def execute(
        self,
        groups: list[DuplicateGroup],
        issues: list[IntegrityIssue],
        min_file_size: int = 1024
    ) -> ActionPlan:
        """액션 플랜 생성.
        
        Args:
            groups: 중복 그룹 리스트
            issues: 무결성 이슈 리스트
            min_file_size: 최소 파일 크기 (bytes)
        
        Returns:
            ActionPlan
        """
        items = []
        action_id = 1
        
        # 중복 파일 삭제
        for group in groups:
            canonical_id = group.canonical_id
            if not canonical_id:
                continue
            
            for member_id in group.member_ids:
                if member_id == canonical_id:
                    continue
                
                record = self.repository.get(member_id)
                if not record:
                    continue
                
                if _should_delete_duplicate(record, is_canonical=False):
                    item = ActionItem(
                        action_id=action_id,
                        file_id=member_id,
                        action="DELETE",
                        risk="LOW",
                        reason=None
                    )
                    items.append(item)
                    action_id += 1
        
        # 작은 파일 삭제
        for issue in issues:
            if issue.category == "TOO_SHORT" and issue.suggested_fix == "DELETE":
                item = ActionItem(
                    action_id=action_id,
                    file_id=issue.file_id,
                    action="DELETE",
                    risk="LOW",
                    reason=issue.issue_id
                )
                items.append(item)
                action_id += 1
        
        # 요약
        bytes_savable = sum(
            self.repository.get(item.file_id).size 
            for item in items 
            if item.action == "DELETE" and self.repository.get(item.file_id)
        )
        
        summary = {
            "bytes_savable": bytes_savable,
            "files_to_delete": len([i for i in items if i.action == "DELETE"]),
            "total_actions": len(items)
        }
        
        return ActionPlan(
            plan_id=1,
            created_from="DUPLICATE",
            items=items,
            summary=summary
        )

