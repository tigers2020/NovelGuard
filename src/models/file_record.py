"""
FileRecord 모델

파일 정보를 나타내는 Pydantic 모델입니다.
"""

from pathlib import Path
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


class FileRecord(BaseModel):
    """파일 정보를 나타내는 데이터 모델.
    
    Attributes:
        path: 파일 경로 (Path 객체)
        name: 파일명
        size: 파일 크기 (바이트)
        encoding: 파일 인코딩 (기본값: "-")
        title: 제목 추출 결과 (원본, 캐싱용)
        normalized_title: 제목 정규화 결과 (그룹핑용)
        episode_range: 회차 범위 (시작, 끝) 튜플
        md5_hash: MD5 해시값 (완전 동일 파일 탐지용)
        normalized_hash: 정규화 해시값 (v1.5용, 선택적)
    """
    
    path: Path
    name: str
    size: int = Field(ge=0, description="파일 크기 (바이트, 0 이상)")
    encoding: str = Field(default="-", description="파일 인코딩")
    
    # 메타데이터 필드 (선택적, 스캔 시 파싱)
    title: Optional[str] = Field(default=None, description="제목 추출 결과 (원본)")
    normalized_title: Optional[str] = Field(default=None, description="제목 정규화 결과 (그룹핑용)")
    episode_range: Optional[tuple[int, int]] = Field(default=None, description="회차 범위 (시작, 끝)")
    
    # 해시 필드 (선택적, 분석 시 계산)
    md5_hash: Optional[str] = Field(default=None, description="MD5 해시값 (완전 동일 파일 탐지용)")
    normalized_hash: Optional[str] = Field(default=None, description="정규화 해시값 (v1.5용)")
    
    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """파일명 유효성 검사.
        
        Args:
            v: 파일명 문자열
            
        Returns:
            검증된 파일명
            
        Raises:
            ValueError: 파일명이 비어있을 때
        """
        if not v or not v.strip():
            raise ValueError("파일명은 비어있을 수 없습니다.")
        return v.strip()
    
    @field_validator("path")
    @classmethod
    def validate_path(cls, v: Path) -> Path:
        """경로 유효성 검사.
        
        Args:
            v: 경로 객체
            
        Returns:
            검증된 경로 객체
        """
        if not isinstance(v, Path):
            v = Path(v)
        return v
    
    # Pydantic v2 설정
    model_config = ConfigDict(
        arbitrary_types_allowed=True,  # Path 타입 허용
        frozen=False,  # 불변 객체 아님 (필요시 수정 가능)
    )

