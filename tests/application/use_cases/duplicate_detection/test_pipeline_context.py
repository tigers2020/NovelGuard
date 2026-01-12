"""PipelineContext 테스트."""
from datetime import datetime
from pathlib import Path

import pytest

from application.dto.duplicate_detection_request import DuplicateDetectionRequest
from application.use_cases.duplicate_detection.stages.base_stage import PipelineContext
from domain.entities.file_entry import FileEntry
from domain.value_objects.filename_parse_result import FilenameParseResult


def test_pipeline_context_initialization():
    """PipelineContext 초기화 테스트."""
    request = DuplicateDetectionRequest(run_id=1)
    context = PipelineContext(request=request)
    
    assert context.request == request
    assert context.files == []
    assert context.parse_results == {}
    assert context.file_id_mapping == {}
    assert context.file_entries_map == {}
    assert context.file_parse_pairs == []
    assert context.blocking_groups == []
    assert context.results == []
    assert context.error is None


def test_pipeline_context_with_data():
    """PipelineContext 데이터 설정 테스트."""
    request = DuplicateDetectionRequest(run_id=1)
    context = PipelineContext(request=request)
    
    # 파일 추가
    file_entry = FileEntry(
        path=Path("test.txt"),
        size=100,
        mtime=datetime.now(),
        extension=".txt",
        file_id=1
    )
    context.files.append(file_entry)
    
    # 파싱 결과 추가
    parse_result = FilenameParseResult(
        original_path=Path("test.txt"),
        original_name="test",
        series_title_norm="test",
        confidence=0.9
    )
    context.parse_results[1] = parse_result
    
    assert len(context.files) == 1
    assert len(context.parse_results) == 1
    assert context.parse_results[1] == parse_result


def test_pipeline_context_error():
    """PipelineContext 에러 설정 테스트."""
    request = DuplicateDetectionRequest(run_id=1)
    context = PipelineContext(request=request)
    
    context.error = "Test error"
    
    assert context.error == "Test error"
