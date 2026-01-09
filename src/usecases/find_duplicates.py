"""중복 탐지 유스케이스."""

from typing import Callable, Optional
from infra.db.file_repository import FileRepository
from domain.models.duplicate_group import DuplicateGroup
from domain.models.file_record import FileRecord
from domain.models.evidence import Evidence
from domain.services.canonical_selector import CanonicalSelector
from common.logging import setup_logging

logger = setup_logging()


def _is_exact_duplicate(record_a: FileRecord, record_b: FileRecord) -> bool:
    """완전 중복 판정 (v1 내부 함수, v1.5에서 DuplicatePolicy로 분리 예정).
    
    Args:
        record_a: 파일 A 레코드
        record_b: 파일 B 레코드
    
    Returns:
        완전 중복 여부
    """
    # 강한 해시가 모두 있고 같으면 완전 중복
    if record_a.hash_strong and record_b.hash_strong:
        return record_a.hash_strong == record_b.hash_strong
    
    # 정규화 지문이 모두 있고 같으면 완전 중복
    if record_a.fingerprint_norm and record_b.fingerprint_norm:
        return record_a.fingerprint_norm == record_b.fingerprint_norm
    
    return False


def _is_similar(
    record_a: FileRecord,
    record_b: FileRecord,
    threshold: float = 0.95
) -> bool:
    """유사도 기반 판정 (v1 내부 함수, v1.5에서 DuplicatePolicy로 분리 예정).
    
    Args:
        record_a: 파일 A 레코드
        record_b: 파일 B 레코드
        threshold: 유사도 임계값 (0.0 ~ 1.0)
    
    Returns:
        유사 여부
    """
    # SimHash가 모두 있으면 SimHash 거리로 판정
    if record_a.simhash64 is not None and record_b.simhash64 is not None:
        # Hamming distance 계산
        distance = bin(record_a.simhash64 ^ record_b.simhash64).count('1')
        # 64bit SimHash 기준 유사도 = 1 - (distance / 64)
        similarity = 1.0 - (distance / 64.0)
        return similarity >= threshold
    
    # 빠른 지문이 모두 있고 같으면 유사로 판정
    if record_a.fingerprint_fast and record_b.fingerprint_fast:
        if record_a.fingerprint_fast == record_b.fingerprint_fast:
            return True
    
    return False


def _is_containment(
    record_a: FileRecord,
    record_b: FileRecord
) -> tuple[bool, Optional[str]]:
    """포함 관계 판정 (v1 내부 함수, v1.5에서 DuplicatePolicy로 분리 예정).
    
    Args:
        record_a: 파일 A 레코드
        record_b: 파일 B 레코드
    
    Returns:
        (포함 관계 여부, 포함 방향: "A_IN_B" | "B_IN_A" | None)
    """
    # 크기 비교로 포함 관계 추정 (실제 구현은 텍스트 비교 필요)
    if record_a.size < record_b.size:
        # A가 B에 포함될 가능성
        return True, "A_IN_B"
    elif record_b.size < record_a.size:
        # B가 A에 포함될 가능성
        return True, "B_IN_A"
    
    return False, None


class FindDuplicatesUseCase:
    """중복 탐지 유스케이스."""
    
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
        similarity_threshold: float = 0.95,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> list[DuplicateGroup]:
        """중복 탐지 실행.
        
        Args:
            similarity_threshold: 유사도 임계값
            progress_callback: 진행 상황 콜백
        
        Returns:
            DuplicateGroup 리스트
        """
        records = list(self.repository.list_all())
        groups = []
        processed = set()
        group_id = 1
        
        total = len(records)
        
        for idx, record_a in enumerate(records):
            if record_a.file_id in processed:
                continue
            
            if progress_callback:
                progress_callback(idx + 1, total)
            
            # 같은 해시를 가진 파일 찾기
            duplicates = [record_a]
            for record_b in records:
                if record_b.file_id == record_a.file_id:
                    continue
                if record_b.file_id in processed:
                    continue
                
                if _is_exact_duplicate(record_a, record_b):
                    duplicates.append(record_b)
                    processed.add(record_b.file_id)
            
            if len(duplicates) > 1:
                # Canonical 선택
                canonical = self.selector.select_canonical(duplicates)
                
                group = DuplicateGroup(
                    group_id=group_id,
                    group_type="EXACT",
                    member_ids=[r.file_id for r in duplicates],
                    canonical_id=canonical.file_id if canonical else None,
                    confidence=1.0,
                    status="CANDIDATE"
                )
                groups.append(group)
                group_id += 1
                processed.add(record_a.file_id)
        
        return groups

