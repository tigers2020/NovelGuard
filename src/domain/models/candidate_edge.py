"""CandidateEdge 도메인 모델 (선택적).

두 파일의 관계를 증거와 함께 담는 구조 (그래프 기반).
"""

from pydantic import BaseModel, Field


class CandidateEdge(BaseModel):
    """후보 엣지 모델 (Union-Find 이유 추적, 포함 관계에도 유용).
    
    Attributes:
        a_id: 파일 A ID
        b_id: 파일 B ID
        relation: 관계 타입 ("EXACT" | "NEAR" | "CONTAINS_A_IN_B" | "CONTAINS_B_IN_A")
        score: 점수 (0.0 ~ 1.0)
        evidence: 증거 ID
    """
    
    a_id: int = Field(..., description="파일 A ID")
    b_id: int = Field(..., description="파일 B ID")
    relation: str = Field(..., description="관계 타입")
    score: float = Field(default=0.0, ge=0.0, le=1.0, description="점수")
    evidence: int = Field(..., description="증거 ID")

