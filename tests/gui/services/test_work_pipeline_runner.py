"""Tests for WorkPipelineRunner (mocked sections)."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import QObject

from application.dto.scan_result import ScanResult
from gui.services.work_pipeline_runner import WorkPipelineRunner


class _ScanVM(QObject):
    def __init__(self) -> None:
        super().__init__()
        self.is_scanning = False

    def scan_completed(self):
        from PySide6.QtCore import Signal

        return Signal(ScanResult)


@pytest.fixture
def runner_parts(qapp):
    main = MagicMock()
    library = MagicMock()
    duplicate = MagicMock()
    move = MagicMock()
    finalize = MagicMock()

    scan_vm = MagicMock()
    scan_vm.is_scanning = False
    library.scan_view_model = scan_vm
    library.set_scan_folder = MagicMock()
    library.request_full_scan = MagicMock()

    dup_vm = MagicMock()
    duplicate.duplicate_view_model = dup_vm
    duplicate.request_detection = MagicMock()
    duplicate.pipeline_dry_run_preview = MagicMock(return_value=True)
    duplicate.pipeline_start_apply = MagicMock(return_value=False)

    move.pipeline_dry_run_sync = MagicMock(return_value=True)
    move.pipeline_execute_with_confirmation = MagicMock(return_value=True)
    finalize.run_apply_and_integrity_auto = MagicMock(return_value=True)

    runner = WorkPipelineRunner(
        main_window=main,
        library=library,
        duplicate=duplicate,
        move=move,
        finalize=finalize,
    )
    return runner, main, library, scan_vm, duplicate, move


def test_runner_start_switches_to_work_and_begins_scan(runner_parts) -> None:
    runner, main, library, scan_vm, *_ = runner_parts
    runner.start(Path("/tmp/scan"))
    main._switch_tab.assert_called_with("work")
    library.set_scan_folder.assert_called_once()
    library.request_full_scan.assert_called_once()


def test_runner_cancel_emits_cancelled(runner_parts) -> None:
    runner, *_ = runner_parts
    finished: list[str] = []
    runner.finished.connect(finished.append)
    runner.cancel()
    assert finished == ["cancelled"]
