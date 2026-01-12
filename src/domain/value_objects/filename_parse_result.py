"""파일명 파싱 결과 ValueObject."""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from domain.value_objects.range_segment import RangeSegment


@dataclass(frozen=True)
class FilenameParseResult:
    """파일명 파싱 결과.
    
    파일명에서 추출한 작품명, 범위, 태그 정보를 담는 불변 객체.
    중복 탐지의 핵심 데이터로 사용됨.
    """
    
    # 원본
    original_path: Path
    """원본 파일 경로."""
    
    original_name: str
    """확장자 제거한 파일명."""
    
    # 파싱 결과
    series_title_norm: str
    """작품명 정규화 (공백/특수문자/태그 제거, 소문자).
    
    예: "작품명 1-170.txt" → "작품명"
        "작품명 1-200(完, 후기 포함)@경우.txt" → "작품명"
    """
    
    range_start: Optional[int] = None
    """시작 범위 (예: 1, 0). None이면 범위 추출 실패.
    
    하위 호환성을 위해 유지. primary segment의 start와 동일.
    """
    
    range_end: Optional[int] = None
    """끝 범위 (예: 170, 1445). None이면 범위 추출 실패.
    
    하위 호환성을 위해 유지. primary segment의 end와 동일.
    """
    
    range_unit: Optional[str] = None
    """범위 단위 (예: "화", "권", "장"). None이면 단위 없음.
    
    하위 호환성을 위해 유지. primary segment의 unit과 동일.
    """
    
    segments: list[RangeSegment] = None
    """범위 세그먼트 리스트 (예: [("본편", 1, 1213, None), ("외전", 1, 71, None)]).
    
    복합 케이스 지원 (본편/외전 등). 비어있으면 segments 파싱 실패.
    """
    
    tags: list[str] = None
    """태그 리스트 (예: ["완", "완결", "후기", "@경우"])."""
    
    # 파싱 메타데이터
    confidence: float = 0.0
    """파싱 신뢰도 (0.0 ~ 1.0). 높을수록 파싱 성공 가능성 높음."""
    
    parse_method: str = "fallback"
    """파싱 방법 ("pattern_match", "heuristic", "fallback")."""
    
    def __post_init__(self) -> None:
        """유효성 검증."""
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(f"confidence must be between 0.0 and 1.0: {self.confidence}")
        
        if self.range_start is not None and self.range_start < 0:
            raise ValueError(f"range_start must be >= 0: {self.range_start}")
        
        if self.range_end is not None and self.range_end < 0:
            raise ValueError(f"range_end must be >= 0: {self.range_end}")
        
        if self.range_start is not None and self.range_end is not None:
            if self.range_start > self.range_end:
                raise ValueError(
                    f"range_start ({self.range_start}) must be <= range_end ({self.range_end})"
                )
        
        if self.segments is None:
            object.__setattr__(self, 'segments', [])
        elif not isinstance(self.segments, list):
            raise ValueError(f"segments must be a list: {type(self.segments)}")
        
        # segments와 range_start/end/unit 일관성 확인
        if self.segments:
            primary_segments = [s for s in self.segments if s.is_primary]
            if primary_segments:
                primary = primary_segments[0]
                if self.range_start is not None and self.range_start != primary.start:
                    raise ValueError(
                        f"range_start ({self.range_start}) must match primary segment start ({primary.start})"
                    )
                if self.range_end is not None and self.range_end != primary.end:
                    raise ValueError(
                        f"range_end ({self.range_end}) must match primary segment end ({primary.end})"
                    )
                if self.range_unit is not None and self.range_unit != primary.unit:
                    raise ValueError(
                        f"range_unit ({self.range_unit}) must match primary segment unit ({primary.unit})"
                    )
        
        if self.tags is None:
            object.__setattr__(self, 'tags', [])
        elif not isinstance(self.tags, list):
            raise ValueError(f"tags must be a list: {type(self.tags)}")
    
    @property
    def has_range(self) -> bool:
        """범위 정보가 있는지 여부."""
        return self.range_start is not None and self.range_end is not None
    
    @property
    def has_segments(self) -> bool:
        """세그먼트 정보가 있는지 여부."""
        return len(self.segments) > 0
    
    @property
    def primary_segment(self) -> Optional[RangeSegment]:
        """Primary segment 반환 (segment_type이 None인 첫 번째 세그먼트).
        
        Returns:
            Primary segment. 없으면 None.
        """
        primary_segments = [s for s in self.segments if s.is_primary]
        return primary_segments[0] if primary_segments else None
    
    @property
    def total_coverage(self) -> int:
        """전체 커버리지 (모든 segments의 coverage 합산).
        
        Returns:
            전체 커버리지. segments가 없으면 0.
        """
        if not self.segments:
            return 0
        
        return sum(segment.coverage for segment in self.segments)
    
    @property
    def has_tags(self) -> bool:
        """태그가 있는지 여부."""
        return len(self.tags) > 0
    
    @property
    def is_complete(self) -> bool:
        """완결본 태그가 있는지 여부 (완, 완결, 完 등)."""
        complete_tags = {"완", "완결", "完", "완전판", "완본", "complete", "finished"}
        return any(tag in complete_tags for tag in self.tags)
    
    @property
    def is_epilogue_included(self) -> bool:
        """후기/에필로그 포함 태그가 있는지 여부."""
        epilogue_tags = {"후기", "에필", "에필로그", "epilogue", "afterword"}
        return any(epilogue_tag in tag.lower() for tag in self.tags for epilogue_tag in epilogue_tags)
    
    def range_contains(self, other: "FilenameParseResult") -> bool:
        """다른 파싱 결과의 범위가 이 범위에 포함되는지 확인.
        
        Args:
            other: 비교할 다른 파싱 결과.
        
        Returns:
            other의 범위가 이 범위에 완전히 포함되면 True.
            범위 정보가 없으면 False.
        
        Note:
            segments가 있으면 segments 기반으로 판정.
            없으면 기존 range_start/range_end 기반으로 판정 (하위 호환성).
        """
        # segments 기반 판정 (우선)
        if self.has_segments and other.has_segments:
            # 같은 타입의 세그먼트만 비교
            for self_segment in self.segments:
                for other_segment in other.segments:
                    if self_segment.segment_type == other_segment.segment_type:
                        if self_segment.contains(other_segment):
                            return True
            return False
        
        # 기존 방식 (하위 호환성)
        if not self.has_range or not other.has_range:
            return False
        
        return (
            self.range_start <= other.range_start
            and self.range_end >= other.range_end
        )
    
    def is_same_series(self, other: "FilenameParseResult") -> bool:
        """같은 작품인지 확인.
        
        Args:
            other: 비교할 다른 파싱 결과.
        
        Returns:
            series_title_norm이 동일하면 True.
        """
        return self.series_title_norm == other.series_title_norm
