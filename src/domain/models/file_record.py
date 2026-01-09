"""FileRecord 도메인 모델.

파일 1개를 대표하는 정규화된 레코드.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from datetime import datetime

from pydantic import BaseModel, Field


class FileRecord(BaseModel):
    """파일 1개를 대표하는 정규화된 레코드.
    
    Attributes:
        file_id: 파일 ID (DB PK 또는 런타임 ID)
        path: 파일 경로
        name: 파일명
        ext: 확장자
        size: 파일 크기 (bytes)
        mtime: 수정 시간 (epoch timestamp)
        is_text: 텍스트 파일 여부
        encoding_detected: 감지된 인코딩
        encoding_confidence: 인코딩 감지 신뢰도 (0.0 ~ 1.0)
        newline: 줄바꿈 타입 ("LF" | "CRLF" | "MIXED" | None)
        hash_strong: 강한 해시 (SHA-256 등, 늦게 계산)
        fingerprint_fast: 빠른 지문 (head/mid/tail hash)
        fingerprint_norm: 정규화 텍스트 지문
        simhash64: SimHash 값 (64bit)
        flags: 플래그 집합 (e.g., {"BINARY_SUSPECT", "DECODE_FAIL"})
        errors: 무결성 이슈 참조 리스트
    """
    
    file_id: int = Field(..., description="파일 ID")
    path: Path = Field(..., description="파일 경로")
    name: str = Field(..., description="파일명")
    ext: str = Field(default="", description="확장자")
    size: int = Field(default=0, description="파일 크기 (bytes)")
    mtime: float = Field(default=0.0, description="수정 시간 (epoch)")
    is_text: bool = Field(default=False, description="텍스트 파일 여부")
    encoding_detected: Optional[str] = Field(default=None, description="감지된 인코딩")
    encoding_confidence: Optional[float] = Field(default=None, description="인코딩 감지 신뢰도")
    newline: Optional[str] = Field(default=None, description="줄바꿈 타입")
    hash_strong: Optional[str] = Field(default=None, description="강한 해시 (SHA-256)")
    fingerprint_fast: Optional[str] = Field(default=None, description="빠른 지문")
    fingerprint_norm: Optional[str] = Field(default=None, description="정규화 텍스트 지문")
    simhash64: Optional[int] = Field(default=None, description="SimHash 값 (64bit)")
    flags: set[str] = Field(default_factory=set, description="플래그 집합")
    errors: list[int] = Field(default_factory=list, description="무결성 이슈 ID 리스트")
    
    class Config:
        """Pydantic 설정."""
        arbitrary_types_allowed = True
        json_encoders = {
            Path: str,
            set: list,
        }
    
    @property
    def mtime_datetime(self) -> Optional[datetime]:
        """수정 시간을 datetime 객체로 반환.
        
        Returns:
            datetime 객체 또는 None
        """
        if self.mtime > 0:
            return datetime.fromtimestamp(self.mtime)
        return None

