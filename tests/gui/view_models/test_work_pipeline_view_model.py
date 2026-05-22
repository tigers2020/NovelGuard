"""Tests for WorkPipelineViewModel."""

from gui.models.app_state import AppState
from gui.view_models.work_pipeline_view_model import WorkPipelineViewModel


def test_duplicate_locked_until_scan_done(qapp) -> None:
    vm = WorkPipelineViewModel(app_state=AppState())
    snap = vm.build_snapshot(
        scan_done=False,
        duplicate_done=False,
        duplicate_skipped=False,
        move_done=False,
        move_skipped=False,
    )
    assert snap.steps["duplicate"] == "locked"


def test_duplicate_ready_after_scan_done(qapp) -> None:
    vm = WorkPipelineViewModel(app_state=AppState())
    snap = vm.build_snapshot(
        scan_done=True,
        duplicate_done=False,
        duplicate_skipped=False,
        move_done=False,
        move_skipped=False,
    )
    assert snap.steps["duplicate"] == "ready"
    assert snap.steps["scan"] == "done"


def test_duplicate_skipped_unlocks_move(qapp) -> None:
    vm = WorkPipelineViewModel(app_state=AppState())
    snap = vm.build_snapshot(
        scan_done=True,
        duplicate_done=False,
        duplicate_skipped=True,
        move_done=False,
        move_skipped=False,
    )
    assert snap.steps["duplicate"] == "skipped"
    assert snap.steps["move"] == "ready"
