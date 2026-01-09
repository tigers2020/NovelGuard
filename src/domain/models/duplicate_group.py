"""DuplicateGroup 도메인 모델.

중복군/유사군/포함군을 표현하는 집합 엔티티.
"""

from typing import Optional
from pydantic import BaseModel, Field


class DuplicateGroup(BaseModel):
    """중복군/유사군/포함군을 표현하는 집합 엔티티.
    
    Attributes:
        group_id: 그룹 ID
        group_type: 그룹 타입 ("EXACT" | "NEAR" | "CONTAINMENT")
        member_ids: 멤버 파일 ID 리스트
        canonical_id: 최신본/보존본 파일 ID
        confidence: 신뢰도 (0.0 ~ 1.0)
        bytes_savable: 예상 절감 용량 (bytes)
        status: 상태 ("CANDIDATE" | "VERIFIED" | "PLANNED" | "APPLIED")
        reasons: 증거 ID 리스트
    """
    
    group_id: int = Field(..., description="그룹 ID")
    group_type: str = Field(..., description="그룹 타입")
    member_ids: list[int] = Field(default_factory=list, description="멤버 파일 ID 리스트")
    canonical_id: Optional[int] = Field(default=None, description="최신본/보존본 파일 ID")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="신뢰도")
    bytes_savable: int = Field(default=0, description="예상 절감 용량 (bytes)")
    status: str = Field(default="CANDIDATE", description="상태")
    reasons: list[int] = Field(default_factory=list, description="증거 ID 리스트")
    
    class Config:
        """Pydantic 설정."""
        json_encoders = {
            set: list,
        }

