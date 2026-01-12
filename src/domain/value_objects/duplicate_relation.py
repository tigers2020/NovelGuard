"""중복 관계 ValueObject."""
from dataclasses import dataclass
from typing import Any, Optional


@dataclass(frozen=True)
class ContainmentRelation:
    """포함 관계 - 하나의 파일이 다른 파일의 범위를 포함하는 관계."""
    
    container_file_id: int
    """포함하는 파일 ID (상위본)."""
    
    contained_file_id: int
    """포함되는 파일 ID (하위본)."""
    
    evidence: dict[str, Any]
    """판정 근거 (범위 비교, 태그 등)."""
    
    confidence: float
    """신뢰도 (0.0 ~ 1.0)."""
    
    def __post_init__(self) -> None:
        """유효성 검증."""
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(f"confidence must be between 0.0 and 1.0: {self.confidence}")
        
        if self.container_file_id == self.contained_file_id:
            raise ValueError("container_file_id and contained_file_id must be different")


@dataclass(frozen=True)
class VersionRelation:
    """버전 관계 - 같은 파일의 업데이트/확장 버전."""
    
    newer_file_id: int
    """새로운 파일 ID (최신본)."""
    
    older_file_id: int
    """이전 파일 ID (구버전)."""
    
    evidence: dict[str, Any]
    """판정 근거 (범위 비교, 크기 비교, 수정일 등)."""
    
    confidence: float
    """신뢰도 (0.0 ~ 1.0)."""
    
    def __post_init__(self) -> None:
        """유효성 검증."""
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(f"confidence must be between 0.0 and 1.0: {self.confidence}")
        
        if self.newer_file_id == self.older_file_id:
            raise ValueError("newer_file_id and older_file_id must be different")


@dataclass(frozen=True)
class ExactDuplicateRelation:
    """Exact 중복 관계 - 내용이 100% 동일한 파일."""
    
    file_ids: list[int]
    """중복된 파일 ID 리스트 (2개 이상)."""
    
    evidence: dict[str, Any]
    """판정 근거 (해시 값 등)."""
    
    confidence: float = 1.0
    """신뢰도 (Exact는 항상 1.0)."""
    
    def __post_init__(self) -> None:
        """유효성 검증."""
        if len(self.file_ids) < 2:
            raise ValueError(f"file_ids must contain at least 2 files: {len(self.file_ids)}")
        
        if len(set(self.file_ids)) != len(self.file_ids):
            raise ValueError("file_ids must not contain duplicates")


@dataclass(frozen=True)
class NearDuplicateRelation:
    """Near 중복 관계 - 내용이 거의 동일한 파일 (유사도 기반)."""
    
    file_ids: list[int]
    """유사한 파일 ID 리스트 (2개 이상)."""
    
    similarity_score: float
    """유사도 점수 (0.0 ~ 1.0)."""
    
    evidence: dict[str, Any]
    """판정 근거 (SimHash, MinHash 등)."""
    
    confidence: float
    """신뢰도 (0.0 ~ 1.0)."""
    
    def __post_init__(self) -> None:
        """유효성 검증."""
        if len(self.file_ids) < 2:
            raise ValueError(f"file_ids must contain at least 2 files: {len(self.file_ids)}")
        
        if not (0.0 <= self.similarity_score <= 1.0):
            raise ValueError(f"similarity_score must be between 0.0 and 1.0: {self.similarity_score}")
        
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(f"confidence must be between 0.0 and 1.0: {self.confidence}")
        
        if len(set(self.file_ids)) != len(self.file_ids):
            raise ValueError("file_ids must not contain duplicates")
