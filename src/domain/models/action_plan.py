"""ActionPlan 도메인 모델.

Dry-run과 Apply를 분리하는 핵심 모델.
"""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


class ActionItem(BaseModel):
    """액션 아이템 모델.
    
    Attributes:
        action_id: 액션 ID
        file_id: 파일 ID
        action: 액션 타입 ("DELETE" | "MOVE" | "RENAME" | "CONVERT_ENCODING" | "NORMALIZE_NEWLINE" | "SKIP")
        target_path: 대상 경로 (MOVE/RENAME 시)
        depends_on: 의존 액션 ID 리스트 (충돌 해결/순서)
        risk: 위험도 ("LOW" | "MEDIUM" | "HIGH")
        reason: 근거 (Evidence ID 또는 Issue ID)
    """
    
    action_id: int = Field(..., description="액션 ID")
    file_id: int = Field(..., description="파일 ID")
    action: str = Field(..., description="액션 타입")
    target_path: Optional[str] = Field(default=None, description="대상 경로")
    depends_on: list[int] = Field(default_factory=list, description="의존 액션 ID 리스트")
    risk: str = Field(default="MEDIUM", description="위험도")
    reason: Optional[int] = Field(default=None, description="근거 ID")
    
    class Config:
        """Pydantic 설정."""
        json_encoders = {
            set: list,
        }


class ActionPlan(BaseModel):
    """액션 플랜 모델.
    
    Attributes:
        plan_id: 플랜 ID
        created_from: 생성 원인 ("DUPLICATE" | "SMALL_FILE" | "INTEGRITY" | ...)
        items: 액션 아이템 리스트
        summary: 요약 (dict)
            예: {"bytes_savable": 1024*1024, "files_to_delete": 10}
        created_at: 생성 시각
    """
    
    plan_id: int = Field(..., description="플랜 ID")
    created_from: str = Field(..., description="생성 원인")
    items: list[ActionItem] = Field(default_factory=list, description="액션 아이템 리스트")
    summary: dict = Field(default_factory=dict, description="요약")
    created_at: datetime = Field(default_factory=datetime.now, description="생성 시각")
    
    class Config:
        """Pydantic 설정."""
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }


class ActionResult(BaseModel):
    """액션 결과 모델.
    
    Attributes:
        action_id: 액션 ID
        ok: 성공 여부
        error: 에러 메시지
        before_path: 이전 경로
        after_path: 이후 경로
        timestamp: 실행 시각
    """
    
    action_id: int = Field(..., description="액션 ID")
    ok: bool = Field(default=False, description="성공 여부")
    error: Optional[str] = Field(default=None, description="에러 메시지")
    before_path: Optional[str] = Field(default=None, description="이전 경로")
    after_path: Optional[str] = Field(default=None, description="이후 경로")
    timestamp: datetime = Field(default_factory=datetime.now, description="실행 시각")
    
    class Config:
        """Pydantic 설정."""
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }

