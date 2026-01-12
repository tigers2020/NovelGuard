"""중복 그룹 결과 DTO."""
from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class DuplicateGroupResult:
    """중복 그룹 결과 DTO."""
    
    group_id: int
    """그룹 ID."""
    
    duplicate_type: str
    """중복 타입 ("exact", "version", "containment", "near")."""
    
    file_ids: list[int]
    """중복된 파일 ID 리스트."""
    
    recommended_keeper_id: Optional[int] = None
    """추천 keeper 파일 ID (None이면 추천 없음)."""
    
    evidence: dict[str, Any] = None
    """판정 근거 (해시 값, 범위 비교 등)."""
    
    confidence: float = 0.0
    """신뢰도 (0.0 ~ 1.0)."""
    
    def __post_init__(self) -> None:
        """유효성 검증."""
        if self.duplicate_type not in ["exact", "version", "containment", "near"]:
            raise ValueError(
                f"duplicate_type must be one of ['exact', 'version', 'containment', 'near']: "
                f"{self.duplicate_type}"
            )
        
        if not self.file_ids:
            raise ValueError("file_ids must not be empty")
        
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(f"confidence must be between 0.0 and 1.0: {self.confidence}")
        
        if self.evidence is None:
            object.__setattr__(self, 'evidence', {})
