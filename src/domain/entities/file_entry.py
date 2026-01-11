"""파일 엔티티."""
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class FileEntry:
    """파일 엔티티 - 스캔 결과로 생성되는 불변 객체."""
    
    path: Path
    """파일 경로."""
    
    size: int
    """파일 크기 (바이트)."""
    
    mtime: datetime
    """수정 시간."""
    
    extension: str
    """확장자 (소문자, 점 포함, 예: '.txt'). 확장자 없으면 빈 문자열 ''."""
    
    is_symlink: bool = False
    """심볼릭 링크 여부."""
    
    is_hidden: bool = False
    """숨김 파일 여부."""
    
    def __post_init__(self) -> None:
        """유효성 검증."""
        if self.size < 0:
            raise ValueError("size must be >= 0")
        # 확장자는 빈 문자열이거나 점으로 시작해야 함
        if self.extension and not self.extension.startswith('.'):
            raise ValueError(f"extension must be empty or start with '.': {self.extension}")
