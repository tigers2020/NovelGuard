"""FileMappingStage 테스트."""
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock

import pytest

from application.dto.duplicate_detection_request import DuplicateDetectionRequest
from application.ports.log_sink import ILogSink
from application.use_cases.duplicate_detection.stages.base_stage import (
    PipelineContext,
    PipelineError
)
from application.use_cases.duplicate_detection.stages.file_mapping_stage import (
    FileMappingStage
)
from domain.entities.file_entry import FileEntry
from domain.value_objects.filename_parse_result import FilenameParseResult


def test_file_mapping_stage_name():
    """FileMappingStage 이름 테스트."""
    file_data_store = Mock()
    file_data_store.get_file_id_by_path.return_value = 1
    
    stage = FileMappingStage(file_data_store=file_data_store)
    
    assert stage.name == "FileDataStore 매핑"


def test_file_mapping_stage_execute():
    """FileMappingStage 실행 테스트."""
    file_data_store = Mock()
    log_sink = Mock(spec=ILogSink)
    
    # Mock 파일 엔트리 생성
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
    
    # Mock 설정
    file_data_store.get_file_id_by_path.side_effect = [10, 20]  # FileDataStore file_id
    
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
    
    stage = FileMappingStage(
        file_data_store=file_data_store,
        log_sink=log_sink
    )
    
    request = DuplicateDetectionRequest(run_id=1)
    context = PipelineContext(request=request)
    context.files = [file_entry1, file_entry2]
    context.parse_results = {
        1: parse_result1,
        2: parse_result2
    }
    
    result_context = stage.execute(context)
    
    assert len(result_context.file_parse_pairs) == 2
    assert len(result_context.file_id_mapping) == 2
    assert result_context.file_id_mapping[1] == 10
    assert result_context.file_id_mapping[2] == 20
    assert result_context.file_entries_map[10] == file_entry1
    assert result_context.file_entries_map[20] == file_entry2


def test_file_mapping_stage_execute_no_files():
    """파일이 없는 경우 테스트."""
    file_data_store = Mock()
    
    stage = FileMappingStage(file_data_store=file_data_store)
    
    request = DuplicateDetectionRequest(run_id=1)
    context = PipelineContext(request=request)
    
    result_context = stage.execute(context)
    
    assert len(result_context.file_parse_pairs) == 0
    assert len(result_context.file_id_mapping) == 0
    assert context.error is None


def test_file_mapping_stage_execute_mapping_failure():
    """매핑 실패 (FileDataStore에 없는 파일) 테스트."""
    file_data_store = Mock()
    log_sink = Mock(spec=ILogSink)
    
    # Mock 파일 엔트리 생성
    file_entry = FileEntry(
        path=Path("test.txt"),
        size=100,
        mtime=datetime.now(),
        extension=".txt",
        file_id=1
    )
    
    # Mock 설정: None 반환 (매핑 실패)
    file_data_store.get_file_id_by_path.return_value = None
    
    parse_result = FilenameParseResult(
        original_path=Path("test.txt"),
        original_name="test",
        series_title_norm="test",
        confidence=0.9
    )
    
    stage = FileMappingStage(
        file_data_store=file_data_store,
        log_sink=log_sink
    )
    
    request = DuplicateDetectionRequest(run_id=1)
    context = PipelineContext(request=request)
    context.files = [file_entry]
    context.parse_results = {1: parse_result}
    
    result_context = stage.execute(context)
    
    # 매핑 실패한 파일은 file_parse_pairs에 포함되지 않음
    assert len(result_context.file_parse_pairs) == 0
    # 단일 파일 실패는 매핑률 0%이므로 에러가 설정됨 (50% 미만)
    assert result_context.error is not None
    assert "FileDataStore 동기화 실패" in result_context.error


def test_file_mapping_stage_execute_high_failure_rate():
    """매핑 실패율이 높은 경우 (50% 이상) 테스트."""
    file_data_store = Mock()
    log_sink = Mock(spec=ILogSink)
    
    # Mock 파일 엔트리 생성 (10개)
    file_entries = [
        FileEntry(
            path=Path(f"test{i}.txt"),
            size=100,
            mtime=datetime.now(),
            extension=".txt",
            file_id=i
        )
        for i in range(10)
    ]
    
    # Mock 설정: 처음 3개만 매핑 성공 (30% 성공률, 70% 실패)
    file_data_store.get_file_id_by_path.side_effect = [
        10 if i < 3 else None  # 처음 3개만 매핑 성공
        for i in range(10)
    ]
    
    parse_results = {
        i: FilenameParseResult(
            original_path=Path(f"test{i}.txt"),
            original_name=f"test{i}",
            series_title_norm="test",
            confidence=0.9
        )
        for i in range(10)
    }
    
    stage = FileMappingStage(
        file_data_store=file_data_store,
        log_sink=log_sink
    )
    
    request = DuplicateDetectionRequest(run_id=1)
    context = PipelineContext(request=request)
    context.files = file_entries
    context.parse_results = parse_results
    
    result_context = stage.execute(context)
    
    # 에러가 설정되어야 함
    assert result_context.error is not None
    assert "FileDataStore 동기화 실패" in result_context.error
    assert "매핑률" in result_context.error


def test_file_mapping_stage_execute_no_file_data_store():
    """FileDataStore가 None인 경우 테스트."""
    log_sink = Mock(spec=ILogSink)
    
    stage = FileMappingStage(
        file_data_store=None,  # type: ignore
        log_sink=log_sink
    )
    
    request = DuplicateDetectionRequest(run_id=1)
    context = PipelineContext(request=request)
    context.files = [FileEntry(
        path=Path("test.txt"),
        size=100,
        mtime=datetime.now(),
        extension=".txt",
        file_id=1
    )]
    
    result_context = stage.execute(context)
    
    assert result_context.error is not None
    assert "FileDataStore is required" in result_context.error
