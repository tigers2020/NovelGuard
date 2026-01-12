"""Blocking 단계."""
from typing import Optional

from application.ports.log_sink import ILogSink
from application.use_cases.duplicate_detection.stages.base_stage import (
    PipelineContext,
    PipelineStage
)
from application.utils.debug_logger import debug_step
from domain.services.blocking_service import BlockingService


class BlockingStage(PipelineStage):
    """Blocking 단계.
    
    파일명 파싱 결과를 기반으로 Blocking 그룹을 생성합니다.
    """
    
    def __init__(
        self,
        blocking_service: BlockingService,
        log_sink: Optional[ILogSink] = None
    ) -> None:
        """Blocking 단계 초기화.
        
        Args:
            blocking_service: Blocking 서비스.
            log_sink: 로그 싱크 (선택적).
        """
        self._blocking_service = blocking_service
        self._log_sink = log_sink
    
    @property
    def name(self) -> str:
        return "Blocking"
    
    def execute(self, context: PipelineContext) -> PipelineContext:
        """Blocking 단계 실행.
        
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
        
        if len(context.file_parse_pairs) == 0:
            # 파일이 없으면 빈 blocking_groups로 반환
            context.blocking_groups = []
            return context
        
        blocking_groups = self._blocking_service.create_blocking_groups(context.file_parse_pairs)
        
        context.blocking_groups = blocking_groups
        
        debug_step(
            self._log_sink,
            "duplicate_detection_blocking_complete",
            {
                "blocking_groups_count": len(blocking_groups),
                "total_files": len(context.file_parse_pairs)
            }
        )
        
        return context
