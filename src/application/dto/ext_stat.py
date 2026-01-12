"""확장자 통계 DTO."""
from dataclasses import dataclass


@dataclass
class ExtStat:
    """확장자별 통계."""
    
    ext: str
    """확장자 (예: ".txt"). 확장자 없으면 빈 문자열."""
    
    count: int
    """파일 수."""
    
    total_bytes: int
    """총 바이트 수."""
