"""Tests for PipelineRunConfirmSheet."""

from gui.services.pipeline_run_preview import PipelineRunPreview
from gui.views.work.pipeline_run_confirm_sheet import PipelineRunConfirmSheet


def test_confirm_requires_checkbox(qapp) -> None:
    sheet = PipelineRunConfirmSheet()
    preview = PipelineRunPreview(
        folder_path="/tmp/x",
        total_files=10,
        duplicate_groups=1,
        duplicate_move_count=3,
        organize_dry_run_total=5,
    )
    sheet.set_preview(preview)
    assert not sheet.is_confirmed()
    sheet._confirm_check.setChecked(True)
    assert sheet.is_confirmed()


def test_start_disabled_until_checkbox(qapp) -> None:
    sheet = PipelineRunConfirmSheet()
    sheet.set_preview(
        PipelineRunPreview(
            folder_path="/x",
            total_files=1,
            duplicate_groups=0,
            duplicate_move_count=0,
            organize_dry_run_total=0,
        )
    )
    assert not sheet._start_btn.isEnabled()
    sheet._confirm_check.setChecked(True)
    assert sheet._start_btn.isEnabled()


def test_confirmed_signal_on_start(qapp) -> None:
    sheet = PipelineRunConfirmSheet()
    sheet.set_preview(
        PipelineRunPreview(
            folder_path="/x",
            total_files=1,
            duplicate_groups=0,
            duplicate_move_count=0,
            organize_dry_run_total=0,
        )
    )
    got: list[bool] = []
    sheet.confirmed.connect(lambda: got.append(True))
    sheet._confirm_check.setChecked(True)
    sheet._start_btn.click()
    assert got
