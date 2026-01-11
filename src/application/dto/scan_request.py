"""스캔 요청 DTO."""
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class ScanRequest:
    """스캔 요청 DTO."""
    
    root_folder: Path
    """스캔할 루트 폴더."""
    
    extensions: Optional[list[str]] = None
    """필터링할 확장자 리스트. None이면 모든 파일, 빈 리스트면 기본 텍스트 확장자."""
    
    include_subdirs: bool = True
    """하위 폴더 포함 여부."""
    
    include_hidden: bool = False
    """숨김 파일 포함 여부."""
    
    include_symlinks: bool = True
    """심볼릭 링크 포함 여부."""
    
    incremental: bool = True
    """증분 스캔 여부 (캐시 사용, Phase 1에서는 미사용)."""
