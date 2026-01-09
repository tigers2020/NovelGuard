"""FileRow ViewModel - 경량화된 UI용 모델."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True, slots=True)
class FileRow:
    """경량화된 UI용 파일 행 모델.
    
    표시/정렬/필터에 필요한 최소 필드만 포함.
    """
    
    file_id: int
    group_id: Optional[int] = None
    group_type: Optional[str] = None
    canonical: bool = False
    similarity: Optional[float] = None
    contains_role: Optional[str] = None  # "CONTAINER" | "CONTAINED" | None
    issues_count: int = 0
    planned_action: Optional[str] = None
    action_status: str = "—"  # "—" | "PLANNED" | "APPLIED" | "FAILED"
    short_path: str = ""  # 표시용 짧은 경로
    size: int = 0
    mtime: float = 0.0
    encoding: Optional[str] = None

