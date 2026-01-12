"""FilenameParsingStage 테스트."""
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock

import pytest

from application.dto.duplicate_detection_request import DuplicateDetectionRequest
from application.ports.index_repository import IIndexRepository
from application.ports.log_sink import ILogSink
from application.use_cases.duplicate_detection.stages.base_stage import PipelineContext
from application.use_cases.duplicate_detection.stages.filename_parsing_stage import (
    FilenameParsingStage
)
from domain.entities.file_entry import FileEntry
from domain.services.filename_parser import FilenameParser
from domain.value_objects.filename_parse_result import FilenameParseResult


def test_filename_parsing_stage_name():
    """FilenameParsingStage 이름 테스트."""
    filename_parser = FilenameParser()
    index_repository = Mock(spec=IIndexRepository)
    
    stage = FilenameParsingStage(
        filename_parser=filename_parser,
        index_repository=index_repository
    )
    
    assert stage.name == "파일명 파싱"


def test_filename_parsing_stage_execute():
    """FilenameParsingStage 실행 테스트."""
    filename_parser = FilenameParser()
    index_repository = Mock(spec=IIndexRepository)
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
    index_repository.list_files.side_effect = [
        [file_entry1, file_entry2],  # 첫 번째 배치
        []  # 두 번째 배치 (빈 리스트로 종료)
    ]
    
    stage = FilenameParsingStage(
        filename_parser=filename_parser,
        index_repository=index_repository,
        log_sink=log_sink
    )
    
    request = DuplicateDetectionRequest(run_id=1)
    context = PipelineContext(request=request)
    
    result_context = stage.execute(context)
    
    assert len(result_context.files) == 2
    assert len(result_context.parse_results) == 2
    assert 1 in result_context.parse_results
    assert 2 in result_context.parse_results
    assert isinstance(result_context.parse_results[1], FilenameParseResult)
    assert isinstance(result_context.parse_results[2], FilenameParseResult)


def test_filename_parsing_stage_execute_no_files():
    """파일이 없는 경우 테스트."""
    filename_parser = FilenameParser()
    index_repository = Mock(spec=IIndexRepository)
    
    # Mock 설정: 빈 리스트 반환
    index_repository.list_files.return_value = []
    
    stage = FilenameParsingStage(
        filename_parser=filename_parser,
        index_repository=index_repository
    )
    
    request = DuplicateDetectionRequest(run_id=1)
    context = PipelineContext(request=request)
    
    result_context = stage.execute(context)
    
    assert len(result_context.files) == 0
    assert len(result_context.parse_results) == 0


def test_filename_parsing_stage_execute_pagination():
    """페이지네이션 테스트."""
    filename_parser = FilenameParser()
    index_repository = Mock(spec=IIndexRepository)
    
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
    file_entry3 = FileEntry(
        path=Path("test3.txt"),
        size=300,
        mtime=datetime.now(),
        extension=".txt",
        file_id=3
    )
    
    # Mock 설정: 첫 번째 배치 2개, 두 번째 배치 1개, 세 번째 빈 리스트
    index_repository.list_files.side_effect = [
        [file_entry1, file_entry2],  # 첫 번째 배치
        [file_entry3],  # 두 번째 배치
        []  # 세 번째 배치 (빈 리스트로 종료)
    ]
    
    stage = FilenameParsingStage(
        filename_parser=filename_parser,
        index_repository=index_repository
    )
    
    request = DuplicateDetectionRequest(run_id=1)
    context = PipelineContext(request=request)
    
    result_context = stage.execute(context)
    
    assert len(result_context.files) == 3
    assert len(result_context.parse_results) == 3
    assert 1 in result_context.parse_results
    assert 2 in result_context.parse_results
    assert 3 in result_context.parse_results


def test_filename_parsing_stage_execute_no_file_id():
    """file_id가 없는 경우 테스트."""
    filename_parser = FilenameParser()
    index_repository = Mock(spec=IIndexRepository)
    
    # Mock 파일 엔트리 생성 (file_id=None)
    file_entry = FileEntry(
        path=Path("test.txt"),
        size=100,
        mtime=datetime.now(),
        extension=".txt",
        file_id=None
    )
    
    # Mock 설정
    index_repository.list_files.side_effect = [
        [file_entry],
        []
    ]
    
    stage = FilenameParsingStage(
        filename_parser=filename_parser,
        index_repository=index_repository
    )
    
    request = DuplicateDetectionRequest(run_id=1)
    context = PipelineContext(request=request)
    
    result_context = stage.execute(context)
    
    assert len(result_context.files) == 1
    # file_id가 없으면 hash 기반으로 저장됨
    assert len(result_context.parse_results) == 1


def test_filename_parsing_stage_execute_parsing_error():
    """파싱 오류 발생 시 테스트 (잘못된 범위 등)."""
    from unittest.mock import Mock, patch
    
    filename_parser = FilenameParser()
    index_repository = Mock(spec=IIndexRepository)
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
    index_repository.list_files.side_effect = [
        [file_entry1, file_entry2],
        []
    ]
    
    # 첫 번째 파일은 정상 파싱, 두 번째 파일은 파싱 오류 발생
    def mock_parse(path: Path) -> FilenameParseResult:
        if path == file_entry2.path:
            # 잘못된 범위로 인한 검증 오류 시뮬레이션
            from domain.value_objects.range_segment import RangeSegment
            # start > end인 경우 ValueError 발생
            raise ValueError("start (275) must be <= end (99)")
        # 정상 파싱
        return FilenameParseResult(
            original_path=path,
            original_name=path.stem,
            series_title_norm="test",
            confidence=0.9
        )
    
    stage = FilenameParsingStage(
        filename_parser=filename_parser,
        index_repository=index_repository,
        log_sink=log_sink
    )
    
    # parse 메서드를 mock으로 교체
    with patch.object(filename_parser, 'parse', side_effect=mock_parse):
        request = DuplicateDetectionRequest(run_id=1)
        context = PipelineContext(request=request)
        
        result_context = stage.execute(context)
        
        # 두 파일 모두 files에 포함됨
        assert len(result_context.files) == 2
        # 하지만 파싱 오류가 발생한 파일은 parse_results에 포함되지 않음
        assert len(result_context.parse_results) == 1
        assert 1 in result_context.parse_results
        assert 2 not in result_context.parse_results
        
        # 로그가 기록되었는지 확인
        assert log_sink.write.called
