"""DuplicateViewModel과 IJobRunner(subscribe / start_duplicate_detection) 계약 테스트."""

from unittest.mock import Mock

from PySide6.QtWidgets import QApplication

from application.dto.duplicate_detection_request import DuplicateDetectionRequest
from application.dto.duplicate_group_result import DuplicateGroupResult
from application.dto.job_types import JobEvent, JobType
from application.ports.index_repository import IIndexRepository
from application.ports.job_runner import IJobRunner
from gui.view_models.duplicate_view_model import DuplicateViewModel


def test_subscribe_receives_duplicate_completed(qapp: QApplication) -> None:
    job_manager = Mock(spec=IJobRunner)
    captured: list = []

    def capture_subscribe(listener):
        captured.append(listener)

    job_manager.subscribe.side_effect = capture_subscribe
    job_manager.start_duplicate_detection.return_value = 1

    index_repository = Mock(spec=IIndexRepository)
    index_repository.get_latest_run_id.return_value = 42

    vm = DuplicateViewModel(job_manager=job_manager, index_repository=index_repository)
    assert len(captured) == 1
    listener = captured[0]

    vm.start_duplicate_detection()
    job_manager.start_duplicate_detection.assert_called_once()
    req = job_manager.start_duplicate_detection.call_args[0][0]
    assert isinstance(req, DuplicateDetectionRequest)
    assert req.run_id == 42

    listener(
        JobEvent(
            job_id=1,
            job_type=JobType.DUPLICATE,
            event_type="started",
            data={},
        )
    )
    assert vm.is_detecting is True

    results = [
        DuplicateGroupResult(
            group_id=1,
            duplicate_type="exact",
            file_ids=[1, 2],
            confidence=1.0,
        )
    ]
    listener(
        JobEvent(
            job_id=1,
            job_type=JobType.DUPLICATE,
            event_type="completed",
            data={"result": results},
        )
    )
    assert vm.is_detecting is False
    assert vm.results == results


def test_subscribe_duplicate_failed(qapp: QApplication) -> None:
    job_manager = Mock(spec=IJobRunner)
    listeners: list = []

    job_manager.subscribe.side_effect = lambda fn: listeners.append(fn)
    job_manager.start_duplicate_detection.return_value = 7

    index_repository = Mock(spec=IIndexRepository)
    index_repository.get_latest_run_id.return_value = 1

    vm = DuplicateViewModel(job_manager=job_manager, index_repository=index_repository)
    listener = listeners[0]

    vm.start_duplicate_detection()
    listener(
        JobEvent(
            job_id=7,
            job_type=JobType.DUPLICATE,
            event_type="started",
            data={},
        )
    )
    listener(
        JobEvent(
            job_id=7,
            job_type=JobType.DUPLICATE,
            event_type="failed",
            data={"error": "pipeline exploded"},
        )
    )
    assert vm.is_detecting is False
    assert "pipeline exploded" in vm.progress_message
