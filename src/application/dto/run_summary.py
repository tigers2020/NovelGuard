"""Run 요약 DTO."""
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class RunSummary:
    """Run 요약 정보."""
    
    run_id: int
    """Run ID."""
    
    started_at: datetime
    """시작 시간."""
    
    finished_at: Optional[datetime]
    """완료 시간. None이면 진행 중."""
    
    root_path: Path
    """스캔 루트 경로."""
    
    options_json: str
    """스캔 옵션 JSON 문자열 (ScanRequest 직렬화)."""
    
    total_files: int
    """총 파일 수."""
    
    total_bytes: int
    """총 바이트 수."""
    
    elapsed_ms: int
    """경과 시간 (밀리초)."""
    
    status: str
    """상태 ("running", "completed", "failed")."""
    
    error_message: Optional[str] = None
    """에러 메시지. status="failed"일 때 이유 저장."""
