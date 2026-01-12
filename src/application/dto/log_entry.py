"""로그 엔트리 DTO."""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class LogEntry:
    """로그 엔트리."""
    
    timestamp: datetime
    """타임스탬프."""
    
    level: str
    """로그 레벨 ("DEBUG", "INFO", "WARNING", "ERROR")."""
    
    message: str
    """로그 메시지."""
    
    job_id: Optional[int] = None
    """Job ID. JobManager 없을 때는 None."""
    
    context: dict = field(default_factory=dict)
    """추가 컨텍스트 (예: {"file_path": "...", "error_type": "..."})."""
