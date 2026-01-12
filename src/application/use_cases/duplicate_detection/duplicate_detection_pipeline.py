"""중복 탐지 파이프라인."""
from typing import Callable, Optional, TYPE_CHECKING

from application.dto.duplicate_detection_request import DuplicateDetectionRequest
from application.dto.duplicate_group_result import DuplicateGroupResult
from application.ports.index_repository import IIndexRepository
from application.ports.log_sink import ILogSink
from application.use_cases.duplicate_detection.stages.base_stage import (
    PipelineContext,
    PipelineError,
    PipelineStage
)
from application.use_cases.duplicate_detection.stages.blocking_stage import BlockingStage
from application.use_cases.duplicate_detection.stages.file_mapping_stage import FileMappingStage
from application.use_cases.duplicate_detection.stages.filename_parsing_stage import (
    FilenameParsingStage
)
from application.use_cases.duplicate_detection.stages.group_creation_stage import (
    GroupCreationStage
)
from application.use_cases.duplicate_detection.stages.relation_detection_stage import (
    RelationDetectionStage
)
from domain.services.blocking_service import BlockingService
from domain.services.containment_detector import ContainmentDetector
from domain.services.filename_parser import FilenameParser

if TYPE_CHECKING:
    from gui.models.file_data_store import FileDataStore


class DuplicateDetectionPipeline:
    """중복 탐지 파이프라인.
    
    순수 Python 클래스로 도메인 로직만 담당.
    Qt/QThread 의존성 없음.
    """
    
    def __init__(
        self,
        filename_parser: FilenameParser,
        blocking_service: BlockingService,
        containment_detector: ContainmentDetector,
        index_repository: IIndexRepository,
        file_data_store: Optional["FileDataStore"] = None,
        log_sink: Optional[ILogSink] = None
    ) -> None:
        """파이프라인 초기화.
        
        Args:
            filename_parser: 파일명 파서.
            blocking_service: Blocking 서비스.
            containment_detector: 포함/버전 관계 탐지기.
            index_repository: 인덱스 저장소.
            file_data_store: 파일 데이터 저장소 (선택적).
            log_sink: 로그 싱크 (선택적).
        """
        self._filename_parser = filename_parser
        self._blocking_service = blocking_service
        self._containment_detector = containment_detector
        self._index_repository = index_repository
        self._file_data_store = file_data_store
        self._log_sink = log_sink
        
        # 단계 초기화
        self._stages: list[PipelineStage] = [
            FilenameParsingStage(
                filename_parser=filename_parser,
                index_repository=index_repository,
                log_sink=log_sink
            ),
            FileMappingStage(
                file_data_store=file_data_store,  # type: ignore
                log_sink=log_sink
            ),
            BlockingStage(
                blocking_service=blocking_service,
                log_sink=log_sink
            ),
            RelationDetectionStage(
                containment_detector=containment_detector,
                log_sink=log_sink
            ),
            GroupCreationStage(
                file_data_store=file_data_store,
                log_sink=log_sink
            )
        ]
    
    def execute(
        self,
        request: DuplicateDetectionRequest,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        cancellation_check: Optional[Callable[[], bool]] = None
    ) -> list[DuplicateGroupResult]:
        """파이프라인 실행.
        
        Args:
            request: 중복 탐지 요청.
            progress_callback: 진행률 콜백 (processed, total, message).
            cancellation_check: 취소 여부 확인 콜백 (True면 취소됨).
        
        Returns:
            중복 그룹 결과 리스트.
        
        Raises:
            PipelineError: 파이프라인 실행 중 에러 발생 시.
        """
        context = PipelineContext(request=request)
        
        for stage_idx, stage in enumerate(self._stages):
            # 취소 확인
            if cancellation_check and cancellation_check():
                raise PipelineError("Pipeline cancelled")
            
            # 진행률 콜백
            if progress_callback:
                progress_callback(
                    stage_idx,
                    len(self._stages),
                    f"{stage.name} 시작..."
                )
            
            # 단계 실행
            context = stage.execute(context)
            
            # 에러 확인
            if context.error:
                raise PipelineError(context.error)
            
            # 조기 종료 조건 확인 (에러 아님, 정상적인 빈 결과)
            # 1. 파일이 없으면 빈 결과 반환
            if stage_idx == 0 and len(context.files) == 0:  # FilenameParsingStage 후
                return []
            
            # 2. 매핑된 파일이 없으면 빈 결과 반환
            if stage_idx == 1 and len(context.file_parse_pairs) == 0:  # FileMappingStage 후
                return []
            
            # 3. Blocking 그룹이 없으면 빈 결과 반환
            if stage_idx == 2 and len(context.blocking_groups) == 0:  # BlockingStage 후
                return []
        
        return context.results
