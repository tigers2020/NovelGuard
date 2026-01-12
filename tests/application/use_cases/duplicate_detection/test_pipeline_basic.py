"""DuplicateDetectionPipeline 기본 테스트."""
from unittest.mock import Mock

import pytest

from application.dto.duplicate_detection_request import DuplicateDetectionRequest
from application.ports.index_repository import IIndexRepository
from application.ports.log_sink import ILogSink
from application.use_cases.duplicate_detection.duplicate_detection_pipeline import (
    DuplicateDetectionPipeline
)
from application.use_cases.duplicate_detection.stages.base_stage import (
    PipelineContext,
    PipelineError,
    PipelineStage
)
from domain.services.blocking_service import BlockingService
from domain.services.containment_detector import ContainmentDetector
from domain.services.filename_parser import FilenameParser


class MockStage(PipelineStage):
    """Mock Stage."""
    
    def __init__(self, name: str, should_error: bool = False):
        self._name = name
        self._should_error = should_error
    
    @property
    def name(self) -> str:
        return self._name
    
    def execute(self, context: PipelineContext) -> PipelineContext:
        if self._should_error:
            context.error = f"Error in {self._name}"
        return context


def test_pipeline_initialization():
    """Pipeline 초기화 테스트."""
    filename_parser = FilenameParser()
    blocking_service = BlockingService(filename_parser=filename_parser)
    containment_detector = ContainmentDetector()
    index_repository = Mock(spec=IIndexRepository)
    log_sink = Mock(spec=ILogSink)
    
    pipeline = DuplicateDetectionPipeline(
        filename_parser=filename_parser,
        blocking_service=blocking_service,
        containment_detector=containment_detector,
        index_repository=index_repository,
        log_sink=log_sink
    )
    
    assert pipeline._filename_parser == filename_parser
    assert pipeline._blocking_service == blocking_service
    assert pipeline._containment_detector == containment_detector
    assert pipeline._index_repository == index_repository
    assert pipeline._log_sink == log_sink
    assert len(pipeline._stages) == 5  # 5개의 Stage가 초기화됨


def test_pipeline_execute_empty_stages():
    """빈 파일 리스트로 실행 테스트."""
    filename_parser = FilenameParser()
    blocking_service = BlockingService(filename_parser=filename_parser)
    containment_detector = ContainmentDetector()
    index_repository = Mock(spec=IIndexRepository)
    
    # Mock 설정: 빈 리스트 반환
    index_repository.list_files.return_value = []
    
    pipeline = DuplicateDetectionPipeline(
        filename_parser=filename_parser,
        blocking_service=blocking_service,
        containment_detector=containment_detector,
        index_repository=index_repository
    )
    
    request = DuplicateDetectionRequest(run_id=1)
    results = pipeline.execute(request)
    
    assert results == []


def test_pipeline_execute_with_stages():
    """Stage가 있는 경우 실행 테스트."""
    filename_parser = FilenameParser()
    blocking_service = BlockingService(filename_parser=filename_parser)
    containment_detector = ContainmentDetector()
    index_repository = Mock(spec=IIndexRepository)
    
    pipeline = DuplicateDetectionPipeline(
        filename_parser=filename_parser,
        blocking_service=blocking_service,
        containment_detector=containment_detector,
        index_repository=index_repository
    )
    
    # Stage 추가
    stage1 = MockStage("Stage 1")
    stage2 = MockStage("Stage 2")
    pipeline._stages = [stage1, stage2]
    
    request = DuplicateDetectionRequest(run_id=1)
    results = pipeline.execute(request)
    
    assert results == []


def test_pipeline_execute_with_progress_callback():
    """진행률 콜백이 있는 경우 실행 테스트."""
    filename_parser = FilenameParser()
    blocking_service = BlockingService(filename_parser=filename_parser)
    containment_detector = ContainmentDetector()
    index_repository = Mock(spec=IIndexRepository)
    
    pipeline = DuplicateDetectionPipeline(
        filename_parser=filename_parser,
        blocking_service=blocking_service,
        containment_detector=containment_detector,
        index_repository=index_repository
    )
    
    stage1 = MockStage("Stage 1")
    pipeline._stages = [stage1]
    
    progress_calls = []
    
    def progress_callback(processed: int, total: int, message: str) -> None:
        progress_calls.append((processed, total, message))
    
    request = DuplicateDetectionRequest(run_id=1)
    results = pipeline.execute(request, progress_callback=progress_callback)
    
    assert results == []
    assert len(progress_calls) == 1
    assert progress_calls[0][2] == "Stage 1 시작..."


def test_pipeline_execute_with_error():
    """에러가 발생한 경우 테스트."""
    filename_parser = FilenameParser()
    blocking_service = BlockingService(filename_parser=filename_parser)
    containment_detector = ContainmentDetector()
    index_repository = Mock(spec=IIndexRepository)
    
    pipeline = DuplicateDetectionPipeline(
        filename_parser=filename_parser,
        blocking_service=blocking_service,
        containment_detector=containment_detector,
        index_repository=index_repository
    )
    
    stage1 = MockStage("Stage 1", should_error=True)
    pipeline._stages = [stage1]
    
    request = DuplicateDetectionRequest(run_id=1)
    
    with pytest.raises(PipelineError, match="Error in Stage 1"):
        pipeline.execute(request)


def test_pipeline_execute_with_cancellation():
    """취소가 발생한 경우 테스트."""
    filename_parser = FilenameParser()
    blocking_service = BlockingService(filename_parser=filename_parser)
    containment_detector = ContainmentDetector()
    index_repository = Mock(spec=IIndexRepository)
    
    pipeline = DuplicateDetectionPipeline(
        filename_parser=filename_parser,
        blocking_service=blocking_service,
        containment_detector=containment_detector,
        index_repository=index_repository
    )
    
    stage1 = MockStage("Stage 1")
    pipeline._stages = [stage1]
    
    request = DuplicateDetectionRequest(run_id=1)
    
    def cancellation_check() -> bool:
        return True
    
    with pytest.raises(PipelineError, match="Pipeline cancelled"):
        pipeline.execute(request, cancellation_check=cancellation_check)
