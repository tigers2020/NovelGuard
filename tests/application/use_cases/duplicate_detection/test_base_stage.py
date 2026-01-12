"""PipelineStage 추상 클래스 테스트."""
import pytest

from application.dto.duplicate_detection_request import DuplicateDetectionRequest
from application.use_cases.duplicate_detection.stages.base_stage import (
    PipelineContext,
    PipelineStage
)


class TestStage(PipelineStage):
    """테스트용 Stage 구현."""
    
    @property
    def name(self) -> str:
        return "Test Stage"
    
    def execute(self, context: PipelineContext) -> PipelineContext:
        context.results = []  # 빈 결과로 설정
        return context


def test_pipeline_stage_interface():
    """PipelineStage 인터페이스 테스트."""
    stage = TestStage()
    
    assert stage.name == "Test Stage"
    
    request = DuplicateDetectionRequest(run_id=1)
    context = PipelineContext(request=request)
    
    result_context = stage.execute(context)
    
    assert result_context == context
    assert result_context.results == []


def test_pipeline_stage_cannot_instantiate_abstract():
    """추상 클래스 직접 인스턴스화 불가 테스트."""
    with pytest.raises(TypeError):
        PipelineStage()  # type: ignore
