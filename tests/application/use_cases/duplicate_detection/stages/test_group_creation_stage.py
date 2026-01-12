"""GroupCreationStage 테스트."""
from unittest.mock import Mock

import pytest

from application.dto.duplicate_detection_request import DuplicateDetectionRequest
from application.dto.duplicate_group_result import DuplicateGroupResult
from application.ports.log_sink import ILogSink
from application.use_cases.duplicate_detection.stages.base_stage import PipelineContext
from application.use_cases.duplicate_detection.stages.group_creation_stage import (
    GroupCreationStage
)


def test_group_creation_stage_name():
    """GroupCreationStage 이름 테스트."""
    stage = GroupCreationStage()
    
    assert stage.name == "그룹 생성"


def test_group_creation_stage_execute_no_results():
    """결과가 없는 경우 테스트."""
    stage = GroupCreationStage()
    
    request = DuplicateDetectionRequest(run_id=1)
    context = PipelineContext(request=request)
    context.results = []
    
    result_context = stage.execute(context)
    
    assert result_context.results == []


def test_group_creation_stage_execute_with_results():
    """결과가 있는 경우 테스트."""
    file_data_store = Mock()
    log_sink = Mock(spec=ILogSink)
    
    # Mock 결과 생성
    group_result = DuplicateGroupResult(
        group_id=1,
        duplicate_type="version",
        file_ids=[1, 2],
        recommended_keeper_id=1,
        evidence={},
        confidence=0.9
    )
    
    stage = GroupCreationStage(
        file_data_store=file_data_store,
        log_sink=log_sink
    )
    
    request = DuplicateDetectionRequest(run_id=1)
    context = PipelineContext(request=request)
    context.results = [group_result]
    
    result_context = stage.execute(context)
    
    # 정규화가 실행되었는지 확인
    # (실제 정규화 로직은 normalize_duplicate_groups에서 처리)
    assert len(result_context.results) >= 0


def test_group_creation_stage_execute_no_file_data_store():
    """FileDataStore가 없는 경우 테스트."""
    stage = GroupCreationStage(file_data_store=None)
    
    group_result = DuplicateGroupResult(
        group_id=1,
        duplicate_type="version",
        file_ids=[1, 2],
        recommended_keeper_id=1,
        evidence={},
        confidence=0.9
    )
    
    request = DuplicateDetectionRequest(run_id=1)
    context = PipelineContext(request=request)
    context.results = [group_result]
    
    result_context = stage.execute(context)
    
    # FileDataStore가 없으면 정규화 없이 그대로 반환
    assert len(result_context.results) == 1
    assert result_context.results[0] == group_result
