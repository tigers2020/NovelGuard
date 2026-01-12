"""Blocking Group ValueObject."""
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from domain.entities.file_entry import FileEntry
from domain.value_objects.filename_parse_result import FilenameParseResult


@dataclass(frozen=True)
class BlockingGroup:
    """Blocking Group - 후보군 축소를 위한 그룹.
    
    같은 작품명과 확장자를 가진 파일들을 묶는 불변 객체.
    중복 탐지의 효율성을 높이기 위해 사용됨.
    """
    
    # 그룹 키
    series_title_norm: str
    """정규화된 작품명."""
    
    extension: str
    """확장자 ('.txt' 형식)."""
    
    # 그룹 멤버
    file_ids: list[int]
    """그룹에 속한 파일 ID 리스트."""
    
    # 메타데이터
    range_start: Optional[int] = None
    """그룹 내 시작 범위 (범위 정보가 있을 때)."""
    
    def __post_init__(self) -> None:
        """유효성 검증."""
        if not self.file_ids:
            raise ValueError("file_ids must not be empty")
        
        if self.range_start is not None and self.range_start < 0:
            raise ValueError(f"range_start must be >= 0: {self.range_start}")
    
    @property
    def size(self) -> int:
        """그룹 크기 (파일 수)."""
        return len(self.file_ids)
    
    @property
    def has_range_info(self) -> bool:
        """범위 정보가 있는지 여부."""
        return self.range_start is not None
    
    def group_key(self) -> tuple[str, str]:
        """그룹 키 반환.
        
        Returns:
            (series_title_norm, extension) 튜플.
        """
        return (self.series_title_norm, self.extension)
