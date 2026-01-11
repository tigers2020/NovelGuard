"""스캔 결과 DTO."""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from domain.entities.file_entry import FileEntry


@dataclass
class ScanResult:
    """스캔 결과 DTO."""
    
    total_files: int
    """총 파일 수."""
    
    total_bytes: int
    """총 바이트 수."""
    
    entries: list[FileEntry]
    """스캔된 파일 엔트리 리스트."""
    
    elapsed_ms: int
    """경과 시간 (밀리초)."""
    
    warnings_count: int = 0
    """경고 수."""
    
    scan_timestamp: Optional[datetime] = None
    """스캔 타임스탬프."""
