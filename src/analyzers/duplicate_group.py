"""
중복 그룹 데이터 구조

중복 파일 그룹을 나타내는 데이터 모델입니다.
근거(reason, evidence)를 포함하여 로그/디버깅을 용이하게 합니다.
"""

from typing import Any, Optional

from pydantic import BaseModel, Field

from models.file_record import FileRecord


class DuplicateGroup(BaseModel):
    """중복 파일 그룹 데이터 모델.
    
    근거 포함 구조로 로그/디버깅 용이.
    Union-Find로 그룹 형성 후 최종 출력 단계에서만 list[list[FileRecord]]로 변환.
    
    Attributes:
        members: 중복 파일 리스트
        reason: 판정 근거 (EXACT_MD5 / RANGE_INCLUSION / CONTENT_INCLUSION / NORMALIZED_HASH)
        evidence: 판정 증거 (해시값, 범위, 앵커 매치 위치 등)
        confidence: 신뢰도 (0.0 ~ 1.0)
        edges: 관계 엣지 리스트 (선택적, 내부 사용)
    """
    
    members: list[FileRecord] = Field(default_factory=list, description="중복 파일 리스트")
    reason: str = Field(description="판정 근거")
    evidence: dict[str, Any] = Field(default_factory=dict, description="판정 증거")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="신뢰도 (0.0 ~ 1.0)")
    edges: Optional[list[dict[str, Any]]] = Field(
        default=None,
        description="관계 엣지 리스트 (선택적, 내부 사용). 각 엣지는 {file1_idx, file2_idx, reason, evidence} 형태"
    )
    keep_file: Optional[FileRecord] = Field(default=None, description="최신본 파일 (유지할 파일)")
    duplicate_strength: Optional[str] = Field(default=None, description="중복 강도 (WEAK/STRONG/CERTAIN)")
    
    def to_file_record_groups(self) -> list[list[FileRecord]]:
        """list[list[FileRecord]] 형태로 변환합니다.
        
        Returns:
            FileRecord 그룹 리스트
        """
        if not self.members:
            return []
        return [self.members]

