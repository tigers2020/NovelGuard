"""Tests for work pipeline DTOs."""

from gui.view_models.work_pipeline_dto import (
    PipelineRunProgress,
    StepId,
    compute_overall_percent,
)


def test_compute_overall_percent_scan_half() -> None:
    assert compute_overall_percent(step_index=0, step_count=4, intra_step_ratio=0.5) == 12


def test_compute_overall_percent_last_step_complete() -> None:
    assert compute_overall_percent(step_index=3, step_count=4, intra_step_ratio=1.0) == 100


def test_pipeline_run_progress_frozen() -> None:
    progress = PipelineRunProgress(
        run_id="r1",
        current_step_id=StepId.SCAN,
        step_index=0,
        step_label="스캔",
        detail_message="1,000 files",
        overall_percent=12,
        phase="running",
    )
    assert progress.phase == "running"
    assert progress.current_step_id == "scan"
