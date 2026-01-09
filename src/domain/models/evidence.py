"""Evidence 도메인 모델.

중복 판정 근거를 저장하는 모델.
"""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


class Evidence(BaseModel):
    """중복 판정 근거 모델.
    
    Attributes:
        evidence_id: 증거 ID
        kind: 증거 종류 ("HASH_STRONG" | "FP_FAST" | "NORM_HASH" | "SIMHASH" | "CONTAINMENT_RK" | "TEXT_DIFF")
        detail: 상세 정보 (dict)
            예: {"head": "...", "tail": "...", "similarity": 0.93, "match_spans": [(1200, 5600)]}
        created_at: 생성 시각
    """
    
    evidence_id: int = Field(..., description="증거 ID")
    kind: str = Field(..., description="증거 종류")
    detail: dict = Field(default_factory=dict, description="상세 정보")
    created_at: datetime = Field(default_factory=datetime.now, description="생성 시각")
    
    class Config:
        """Pydantic 설정."""
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }

