"""파이프라인 기본 구조."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, TYPE_CHECKING

from application.dto.duplicate_detection_request import DuplicateDetectionRequest
from application.dto.duplicate_group_result import DuplicateGroupResult
from domain.entities.file_entry import FileEntry
from domain.value_objects.blocking_group import BlockingGroup
from domain.value_objects.filename_parse_result import FilenameParseResult

if TYPE_CHECKING:
    from gui.models.file_data_store import FileDataStore


@dataclass
class PipelineContext:
    """파이프라인 컨텍스트.
    
    파이프라인 실행 중 각 단계 간 데이터를 전달하는 컨텍스트 객체.
    각 Stage는 이 컨텍스트를 읽고 업데이트합니다.
    """
    
    request: DuplicateDetectionRequest
    """중복 탐지 요청."""
    
    files: list[FileEntry] = field(default_factory=list)
    """파일 엔트리 리스트 (IndexRepository에서 가져온 원본)."""
    
    parse_results: dict[int, FilenameParseResult] = field(default_factory=dict)
    """파일명 파싱 결과 (IndexRepository file_id 또는 hash -> FilenameParseResult)."""
    
    file_id_mapping: dict[int, int] = field(default_factory=dict)
    """파일 ID 매핑 (IndexRepository file_id 또는 hash -> FileDataStore file_id)."""
    
    file_entries_map: dict[int, FileEntry] = field(default_factory=dict)
    """파일 엔트리 맵 (FileDataStore file_id -> FileEntry)."""
    
    file_parse_pairs: list[tuple[FileEntry, FilenameParseResult]] = field(default_factory=list)
    """파일-파싱 결과 쌍 리스트 (FileDataStore file_id 기준)."""
    
    blocking_groups: list[BlockingGroup] = field(default_factory=list)
    """Blocking 그룹 리스트."""
    
    results: list[DuplicateGroupResult] = field(default_factory=list)
    """중복 그룹 결과 리스트."""
    
    error: Optional[str] = None
    """에러 메시지 (에러 발생 시 설정)."""


class PipelineError(Exception):
    """파이프라인 실행 중 발생한 에러."""
    pass


class PipelineStage(ABC):
    """파이프라인 단계 인터페이스.
    
    각 단계는 이 추상 클래스를 상속받아 구현합니다.
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """단계 이름.
        
        Returns:
            단계 이름 (예: "파일명 파싱").
        """
        pass
    
    @abstractmethod
    def execute(self, context: PipelineContext) -> PipelineContext:
        """단계 실행.
        
        Args:
            context: 파이프라인 컨텍스트.
        
        Returns:
            업데이트된 컨텍스트.
        
        Raises:
            PipelineError: 단계 실행 중 에러 발생 시.
        """
        pass
