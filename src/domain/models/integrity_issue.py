"""IntegrityIssue 도메인 모델.

무결성/인코딩 관련 문제를 표준화하는 모델.
"""

from typing import Optional
from pydantic import BaseModel, Field


class IntegrityIssue(BaseModel):
    """무결성/인코딩 관련 문제 모델.
    
    Attributes:
        issue_id: 이슈 ID
        file_id: 파일 ID
        severity: 심각도 ("INFO" | "WARN" | "ERROR")
        category: 카테고리 ("ENCODING" | "NEWLINE" | "NUL_BYTE" | "BROKEN_TEXT" | "TOO_SHORT" | ...)
        message: 메시지
        metrics: 메트릭 (dict)
            예: {"invalid_char_rate": 0.05, "null_count": 3}
        fixable: 수정 가능 여부
        suggested_fix: 제안된 수정 사항 ("CONVERT_UTF8" | "NORMALIZE_NEWLINE" | ...)
    """
    
    issue_id: int = Field(..., description="이슈 ID")
    file_id: int = Field(..., description="파일 ID")
    severity: str = Field(..., description="심각도")
    category: str = Field(..., description="카테고리")
    message: str = Field(..., description="메시지")
    metrics: dict = Field(default_factory=dict, description="메트릭")
    fixable: bool = Field(default=False, description="수정 가능 여부")
    suggested_fix: Optional[str] = Field(default=None, description="제안된 수정 사항")

