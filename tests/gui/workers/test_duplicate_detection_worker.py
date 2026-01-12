"""DuplicateDetectionWorker 테스트."""
from pathlib import Path
from unittest.mock import Mock

import pytest

from application.dto.duplicate_detection_request import DuplicateDetectionRequest
from application.ports.index_repository import IIndexRepository
from application.ports.log_sink import ILogSink
from application.use_cases.duplicate_detection.stages.base_stage import PipelineError
from gui.workers.duplicate_detection_worker import DuplicateDetectionWorker


def test_worker_initialization():
    """Worker 초기화 테스트."""
    request = DuplicateDetectionRequest(run_id=1)
    index_repository = Mock(spec=IIndexRepository)
    log_sink = Mock(spec=ILogSink)
    
    worker = DuplicateDetectionWorker(
        request=request,
        index_repository=index_repository,
        log_sink=log_sink
    )
    
    assert worker._request == request
    assert worker._index_repository == index_repository
    assert worker._log_sink == log_sink
    assert worker._cancelled is False
    assert worker._pipeline is not None


def test_worker_cancel():
    """Worker 취소 테스트."""
    request = DuplicateDetectionRequest(run_id=1)
    index_repository = Mock(spec=IIndexRepository)
    log_sink = Mock(spec=ILogSink)
    
    worker = DuplicateDetectionWorker(
        request=request,
        index_repository=index_repository,
        log_sink=log_sink
    )
    
    worker.cancel()
    
    assert worker._cancelled is True


def test_worker_run_no_index_repository():
    """IndexRepository가 없는 경우 테스트."""
    request = DuplicateDetectionRequest(run_id=1)
    log_sink = Mock(spec=ILogSink)
    
    worker = DuplicateDetectionWorker(
        request=request,
        index_repository=None,
        log_sink=log_sink
    )
    
    error_emitted = []
    
    def on_error(error: str) -> None:
        error_emitted.append(error)
    
    worker.duplicate_error.connect(on_error)
    worker.run()
    
    assert len(error_emitted) == 1
    assert "IndexRepository is required" in error_emitted[0]


def test_worker_run_pipeline_error():
    """Pipeline 에러 발생 시 테스트."""
    request = DuplicateDetectionRequest(run_id=1)
    index_repository = Mock(spec=IIndexRepository)
    log_sink = Mock(spec=ILogSink)
    
    # Mock Pipeline 설정
    worker = DuplicateDetectionWorker(
        request=request,
        index_repository=index_repository,
        log_sink=log_sink
    )
    
    # Pipeline의 execute를 Mock하여 에러 발생시키기
    if worker._pipeline:
        worker._pipeline.execute = Mock(side_effect=PipelineError("Test error"))
    
    error_emitted = []
    
    def on_error(error: str) -> None:
        error_emitted.append(error)
    
    worker.duplicate_error.connect(on_error)
    worker.run()
    
    assert len(error_emitted) == 1
    assert "Test error" in error_emitted[0]
