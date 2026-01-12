"""Range Segment ValueObject."""
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class RangeSegment:
    """범위 세그먼트 - 복합 범위의 일부 (본편/외전/에필 등).
    
    "본편 1-1213 외전 1-71" 같은 복합 케이스를 처리하기 위한 값 객체.
    """
    
    start: int
    """시작 범위 (예: 1, 0)."""
    
    end: int
    """끝 범위 (예: 1213, 71)."""
    
    segment_type: Optional[str] = None
    """세그먼트 타입 (예: "본편", "외전", "에필", None).
    
    None이면 기본 세그먼트 (primary segment).
    """
    
    unit: Optional[str] = None
    """범위 단위 (예: "화", "권", "장"). None이면 단위 없음."""
    
    def __post_init__(self) -> None:
        """유효성 검증."""
        if self.start < 0:
            raise ValueError(f"start must be >= 0: {self.start}")
        
        if self.end < 0:
            raise ValueError(f"end must be >= 0: {self.end}")
        
        if self.start > self.end:
            raise ValueError(
                f"start ({self.start}) must be <= end ({self.end})"
            )
    
    @property
    def is_primary(self) -> bool:
        """기본 세그먼트인지 여부 (segment_type이 None)."""
        return self.segment_type is None
    
    @property
    def coverage(self) -> int:
        """범위 커버리지 (end - start + 1)."""
        return self.end - self.start + 1
    
    def contains(self, other: "RangeSegment") -> bool:
        """다른 세그먼트가 이 세그먼트에 포함되는지 확인.
        
        Args:
            other: 비교할 다른 세그먼트.
        
        Returns:
            other의 범위가 이 세그먼트에 완전히 포함되면 True.
        """
        return (
            self.start <= other.start
            and self.end >= other.end
        )
    
    def overlaps(self, other: "RangeSegment") -> bool:
        """다른 세그먼트와 겹치는지 확인.
        
        Args:
            other: 비교할 다른 세그먼트.
        
        Returns:
            범위가 겹치면 True.
        """
        return not (self.end < other.start or self.start > other.end)
    
    def __eq__(self, other: object) -> bool:
        """동등성 비교."""
        if not isinstance(other, RangeSegment):
            return False
        
        return (
            self.segment_type == other.segment_type
            and self.start == other.start
            and self.end == other.end
            and self.unit == other.unit
        )
