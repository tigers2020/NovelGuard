"""DuplicateDetectionWorker 테스트."""

from unittest.mock import Mock

from application.dto.duplicate_detection_request import DuplicateDetectionRequest
from application.ports.log_sink import ILogSink
from application.use_cases.duplicate_detection.duplicate_detection_pipeline import (
    DuplicateDetectionPipeline,
)
from application.use_cases.duplicate_detection.stages.base_stage import PipelineError
from gui.workers.duplicate_detection_worker import DuplicateDetectionWorker


def test_worker_initialization():
    """Worker 초기화 테스트."""
    request = DuplicateDetectionRequest(run_id=1)
    pipeline = Mock(spec=DuplicateDetectionPipeline)
    log_sink = Mock(spec=ILogSink)

    worker = DuplicateDetectionWorker(request=request, pipeline=pipeline, log_sink=log_sink)

    assert worker._request == request
    assert worker._pipeline is pipeline
    assert worker._log_sink == log_sink
    assert worker._cancelled is False


def test_worker_cancel():
    """Worker 취소 테스트."""
    request = DuplicateDetectionRequest(run_id=1)
    pipeline = Mock(spec=DuplicateDetectionPipeline)
    log_sink = Mock(spec=ILogSink)

    worker = DuplicateDetectionWorker(request=request, pipeline=pipeline, log_sink=log_sink)

    worker.cancel()

    assert worker._cancelled is True


def test_worker_run_no_pipeline():
    """Pipeline이 없는 경우 테스트."""
    request = DuplicateDetectionRequest(run_id=1)
    log_sink = Mock(spec=ILogSink)

    worker = DuplicateDetectionWorker(request=request, pipeline=None, log_sink=log_sink)

    error_emitted = []

    def on_error(error: str) -> None:
        error_emitted.append(error)

    worker.duplicate_error.connect(on_error)
    worker.run()

    assert len(error_emitted) == 1
    assert "pipeline is required" in error_emitted[0].lower()


def test_worker_run_pipeline_error():
    """Pipeline 에러 발생 시 테스트."""
    request = DuplicateDetectionRequest(run_id=1)
    pipeline = Mock(spec=DuplicateDetectionPipeline)
    pipeline.execute = Mock(side_effect=PipelineError("Test error"))
    log_sink = Mock(spec=ILogSink)

    worker = DuplicateDetectionWorker(request=request, pipeline=pipeline, log_sink=log_sink)

    error_emitted = []

    def on_error(error: str) -> None:
        error_emitted.append(error)

    worker.duplicate_error.connect(on_error)
    worker.run()

    assert len(error_emitted) == 1
    assert "Test error" in error_emitted[0]
