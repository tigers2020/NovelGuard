"""파일 데이터 DTO."""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from domain.entities.file_entry import FileEntry


@dataclass
class FileData:
    """파일 데이터 (확장된 정보 포함)."""

    entry: FileEntry
    """기본 파일 엔트리."""

    file_id: int
    """파일 ID (고유 식별자)."""

    # 중복 관련
    duplicate_group_id: Optional[int] = None
    """중복 그룹 ID (None이면 중복 아님)."""

    is_canonical: bool = False
    """대표 파일 여부 (중복 그룹에서)."""

    similarity_score: Optional[float] = None
    """유사도 점수 (0.0 ~ 1.0)."""

    # 무결성 관련
    integrity_issues: list[str] = field(default_factory=list)
    """무결성 이슈 메시지 리스트."""

    integrity_severity: Optional[str] = None
    """가장 심각한 무결성 이슈 심각도 (INFO, WARN, ERROR)."""

    # 인코딩 관련
    encoding: Optional[str] = None
    """감지된 인코딩."""

    encoding_confidence: Optional[float] = None
    """인코딩 감지 신뢰도 (0.0 ~ 1.0)."""

    @property
    def path(self) -> Path:
        """파일 경로."""
        return self.entry.path

    @property
    def size(self) -> int:
        """파일 크기."""
        return self.entry.size

    @property
    def mtime(self) -> datetime:
        """수정 시간."""
        return self.entry.mtime

    @property
    def extension(self) -> str:
        """확장자."""
        return self.entry.extension
