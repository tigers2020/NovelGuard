"""Tests for WorkPipelineRunner auto_run (no mid-run modals)."""

from pathlib import Path
from unittest.mock import MagicMock

from gui.services.work_pipeline_runner import WorkPipelineRunner


def test_auto_run_skips_dry_run_dialog(qapp) -> None:
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

    dry_run_calls: list[int] = []
    duplicate.pipeline_dry_run_preview = MagicMock(
        side_effect=lambda parent: dry_run_calls.append(1) or True
    )
    duplicate.pipeline_apply_auto = MagicMock(return_value=False)

    move.pipeline_dry_run_sync = MagicMock(return_value=True)
    move.pipeline_execute_auto = MagicMock(return_value=True)
    finalize.run_apply_and_integrity_auto = MagicMock(return_value=True)

    runner = WorkPipelineRunner(
        main_window=main,
        library=library,
        duplicate=duplicate,
        move=move,
        finalize=finalize,
    )
    runner._auto_run = True

    runner._on_duplicate_completed([object()])
    assert dry_run_calls == []
    duplicate.pipeline_apply_auto.assert_called_once()


def test_start_accepts_auto_run_flag(qapp) -> None:
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

    runner = WorkPipelineRunner(
        main_window=main,
        library=library,
        duplicate=duplicate,
        move=move,
        finalize=finalize,
    )
    runner.start(Path("/tmp/x"), auto_run=True)
    assert runner._auto_run is True
