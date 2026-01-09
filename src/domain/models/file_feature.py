"""FileFeature 도메인 모델 (선택적).

FileRecord가 비대해질 때 특징만 분리하는 모델.
"""

from typing import Optional
from pydantic import BaseModel, Field


class FileFeature(BaseModel):
    """파일 특징 모델.
    
    Attributes:
        file_id: 파일 ID
        head_hash: 헤드 해시
        mid_hash: 중간 해시
        tail_hash: 테일 해시
        sample_text_head: 헤드 샘플 텍스트 (프리뷰용)
        token_ngrams_sig: 토큰 n-gram 시그니처 (포함/유사 후보용)
        decoded_ok: 디코딩 성공 여부
        decode_error_rate: 디코딩 에러 비율
    """
    
    file_id: int = Field(..., description="파일 ID")
    head_hash: Optional[str] = Field(default=None, description="헤드 해시")
    mid_hash: Optional[str] = Field(default=None, description="중간 해시")
    tail_hash: Optional[str] = Field(default=None, description="테일 해시")
    sample_text_head: Optional[str] = Field(default=None, description="헤드 샘플 텍스트")
    token_ngrams_sig: Optional[bytes] = Field(default=None, description="토큰 n-gram 시그니처")
    decoded_ok: bool = Field(default=False, description="디코딩 성공 여부")
    decode_error_rate: float = Field(default=0.0, ge=0.0, le=1.0, description="디코딩 에러 비율")

