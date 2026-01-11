"""Preview 스캔 통계 ValueObject."""
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class PreviewStats:
    """Preview 스캔 통계 정보.
    
    폴더 선택 직후 빠른 미리보기 정보를 담는 불변 객체.
    파일 수와 확장자 분포만 포함하며, 실제 파일 메타데이터는 포함하지 않음.
    """
    
    estimated_total_files: int
    """예상 총 파일 수."""
    
    top_extensions: dict[str, int]
    """확장자별 파일 수. {'.txt': 70, '.md': 30} 형식."""
    
    estimated_bytes: Optional[int] = None
    """예상 총 바이트 수 (선택적)."""
    
    def __post_init__(self) -> None:
        """유효성 검증."""
        if self.estimated_total_files < 0:
            raise ValueError("estimated_total_files must be >= 0")
        
        if self.estimated_bytes is not None and self.estimated_bytes < 0:
            raise ValueError("estimated_bytes must be >= 0")
        
        for ext, count in self.top_extensions.items():
            if count < 0:
                raise ValueError(f"Extension count '{ext}' must be >= 0")
    
    @property
    def has_size_estimate(self) -> bool:
        """크기 추정 정보가 있는지 여부."""
        return self.estimated_bytes is not None
    
    @property
    def is_empty(self) -> bool:
        """파일이 없는지 여부."""
        return self.estimated_total_files == 0
    
    @property
    def extension_count(self) -> int:
        """확장자 종류 수."""
        return len(self.top_extensions)
    
    def get_most_common_extension(self) -> Optional[str]:
        """가장 많은 확장자 반환.
        
        Returns:
            가장 많은 확장자 ('.txt' 형식). 파일이 없으면 None.
        """
        if not self.top_extensions:
            return None
        
        return max(self.top_extensions.items(), key=lambda x: x[1])[0]
    
    def get_extension_percentage(self, extension: str) -> float:
        """확장자 비율 계산.
        
        Args:
            extension: 확장자 ('.txt' 형식).
        
        Returns:
            비율 (0.0 ~ 100.0). 파일이 없으면 0.0.
        """
        if self.estimated_total_files == 0:
            return 0.0
        
        count = self.top_extensions.get(extension, 0)
        return (count / self.estimated_total_files) * 100.0
    
    def has_extension(self, extension: str) -> bool:
        """확장자 존재 확인.
        
        Args:
            extension: 확장자 ('.txt' 형식).
        
        Returns:
            확장자가 존재하면 True.
        """
        return extension in self.top_extensions
    
    def get_top_extensions(self, limit: int = 5) -> list[tuple[str, int]]:
        """상위 N개 확장자 반환.
        
        Args:
            limit: 반환할 확장자 개수.
        
        Returns:
            (확장자, 파일 수) 튜플 리스트. 파일 수 기준 내림차순 정렬.
        """
        sorted_exts = sorted(
            self.top_extensions.items(),
            key=lambda x: x[1],
            reverse=True
        )
        return sorted_exts[:limit]
