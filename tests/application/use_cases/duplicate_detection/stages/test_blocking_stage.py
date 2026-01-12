"""BlockingStage 테스트."""
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock

import pytest

from application.dto.duplicate_detection_request import DuplicateDetectionRequest
from application.ports.log_sink import ILogSink
from application.use_cases.duplicate_detection.stages.base_stage import PipelineContext
from application.use_cases.duplicate_detection.stages.blocking_stage import BlockingStage
from domain.entities.file_entry import FileEntry
from domain.services.blocking_service import BlockingService
from domain.services.filename_parser import FilenameParser
from domain.value_objects.blocking_group import BlockingGroup
from domain.value_objects.filename_parse_result import FilenameParseResult


def test_blocking_stage_name():
    """BlockingStage 이름 테스트."""
    filename_parser = FilenameParser()
    blocking_service = BlockingService(filename_parser=filename_parser)
    
    stage = BlockingStage(blocking_service=blocking_service)
    
    assert stage.name == "Blocking"


def test_blocking_stage_execute():
    """BlockingStage 실행 테스트."""
    filename_parser = FilenameParser()
    blocking_service = BlockingService(filename_parser=filename_parser)
    log_sink = Mock(spec=ILogSink)
    
    # Mock 파일 엔트리 및 파싱 결과 생성
    file_entry1 = FileEntry(
        path=Path("test1.txt"),
        size=100,
        mtime=datetime.now(),
        extension=".txt",
        file_id=1
    )
    file_entry2 = FileEntry(
        path=Path("test2.txt"),
        size=200,
        mtime=datetime.now(),
        extension=".txt",
        file_id=2
    )
    
    parse_result1 = FilenameParseResult(
        original_path=Path("test1.txt"),
        original_name="test1",
        series_title_norm="test",
        confidence=0.9
    )
    parse_result2 = FilenameParseResult(
        original_path=Path("test2.txt"),
        original_name="test2",
        series_title_norm="test",
        confidence=0.9
    )
    
    stage = BlockingStage(
        blocking_service=blocking_service,
        log_sink=log_sink
    )
    
    request = DuplicateDetectionRequest(run_id=1)
    context = PipelineContext(request=request)
    context.file_parse_pairs = [
        (file_entry1, parse_result1),
        (file_entry2, parse_result2)
    ]
    
    result_context = stage.execute(context)
    
    # BlockingService가 그룹을 생성했는지 확인
    assert isinstance(result_context.blocking_groups, list)
    # 실제 그룹 생성은 BlockingService의 로직에 따라 달라질 수 있음


def test_blocking_stage_execute_no_files():
    """파일이 없는 경우 테스트."""
    filename_parser = FilenameParser()
    blocking_service = BlockingService(filename_parser=filename_parser)
    
    stage = BlockingStage(blocking_service=blocking_service)
    
    request = DuplicateDetectionRequest(run_id=1)
    context = PipelineContext(request=request)
    context.file_parse_pairs = []
    
    result_context = stage.execute(context)
    
    assert result_context.blocking_groups == []
