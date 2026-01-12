"""Job 타입 및 상태 정의."""
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional


class JobType(str, Enum):
    """Job 타입."""
    
    SCAN = "scan"
    """파일 스캔 작업."""
    
    DUPLICATE = "duplicate"
    """중복 탐지 작업."""
    
    ENCODING = "encoding"
    """인코딩 분석 작업."""
    
    INTEGRITY = "integrity"
    """무결성 검사 작업."""


class JobStatus(str, Enum):
    """Job 상태."""
    
    PENDING = "pending"
    """대기 중."""
    
    RUNNING = "running"
    """실행 중."""
    
    COMPLETED = "completed"
    """완료."""
    
    FAILED = "failed"
    """실패."""
    
    CANCELLED = "cancelled"
    """취소됨."""


@dataclass
class JobProgress:
    """Job 진행률."""
    
    processed: int
    """처리된 항목 수."""
    
    total: Optional[int]
    """총 항목 수. None이면 미정."""
    
    message: str
    """진행 메시지."""


@dataclass
class JobEvent:
    """Job 이벤트."""
    
    job_id: int
    """Job ID."""
    
    job_type: JobType
    """Job 타입."""
    
    event_type: str
    """이벤트 타입 ("started", "progress", "completed", "failed", "cancelled")."""
    
    data: dict[str, Any]
    """이벤트 데이터 (진행률, 결과, 에러 등)."""
