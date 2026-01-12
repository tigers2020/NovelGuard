"""그룹 생성 및 정규화 단계."""
from typing import Optional, TYPE_CHECKING

from application.ports.log_sink import ILogSink
from application.use_cases.duplicate_detection.stages.base_stage import (
    PipelineContext,
    PipelineStage
)
from application.utils.debug_logger import debug_step

if TYPE_CHECKING:
    from gui.models.file_data_store import FileDataStore


class GroupCreationStage(PipelineStage):
    """그룹 생성 및 정규화 단계.
    
    중복 그룹들을 정규화하여 겹침을 제거합니다.
    """
    
    def __init__(
        self,
        file_data_store: Optional["FileDataStore"] = None,
        log_sink: Optional[ILogSink] = None
    ) -> None:
        """그룹 생성 및 정규화 단계 초기화.
        
        Args:
            file_data_store: 파일 데이터 저장소 (선택적, 정규화에 필요).
            log_sink: 로그 싱크 (선택적).
        """
        self._file_data_store = file_data_store
        self._log_sink = log_sink
    
    @property
    def name(self) -> str:
        return "그룹 생성"
    
    def execute(self, context: PipelineContext) -> PipelineContext:
        """그룹 생성 및 정규화 단계 실행.
        
        Args:
            context: 파이프라인 컨텍스트.
        
        Returns:
            업데이트된 컨텍스트.
        """
        debug_step(
            self._log_sink,
            "duplicate_detection_stage",
            {"stage": self.name}
        )
        
        # 그룹 정규화 (겹침 제거)
        normalized_results = context.results
        if context.results and self._file_data_store:
            from application.utils.duplicate_group_normalizer import normalize_duplicate_groups
            
            raw_groups_count = len(context.results)
            normalized_results = normalize_duplicate_groups(context.results, self._file_data_store)
            normalized_groups_count = len(normalized_results)
            
            debug_step(
                self._log_sink,
                "duplicate_detection_groups_normalized",
                {
                    "raw_groups_count": raw_groups_count,
                    "normalized_groups_count": normalized_groups_count,
                    "reduction": raw_groups_count - normalized_groups_count
                }
            )
        
        context.results = normalized_results
        
        return context
