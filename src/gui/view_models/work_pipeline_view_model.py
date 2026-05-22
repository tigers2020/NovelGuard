"""ViewModel for work pipeline step gating and auto-run progress."""

from typing import Optional

from PySide6.QtCore import QObject, Signal

from gui.models.app_state import AppState
from gui.view_models.work_pipeline_dto import (
    FinalizeSubstate,
    PipelineRunProgress,
    PipelineSnapshot,
    StepState,
)


class WorkPipelineViewModel(QObject):
    """Step lock/ready state and pipeline run progress for the Work screen."""

    snapshot_changed = Signal(object)
    run_progress_changed = Signal(object)

    def __init__(self, app_state: AppState, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._app_state = app_state
        self._active_step_id: str | None = None
        self._finalize_substate: FinalizeSubstate = "idle"
        self._run_progress: PipelineRunProgress | None = None

    def build_snapshot(
        self,
        *,
        scan_done: bool,
        duplicate_done: bool,
        duplicate_skipped: bool,
        move_done: bool,
        move_skipped: bool,
        active_step_id: str | None = None,
        finalize_substate: FinalizeSubstate | None = None,
    ) -> PipelineSnapshot:
        """Compute step states from pipeline completion flags."""
        active = active_step_id if active_step_id is not None else self._active_step_id
        finalize = finalize_substate if finalize_substate is not None else self._finalize_substate

        steps: dict[str, StepState] = {
            "scan": "done" if scan_done else "ready",
            "duplicate": (
                "skipped"
                if duplicate_skipped
                else "done" if duplicate_done else "ready" if scan_done else "locked"
            ),
            "move": (
                "skipped"
                if move_skipped
                else (
                    "done"
                    if move_done
                    else "ready" if (duplicate_done or duplicate_skipped) else "locked"
                )
            ),
            "finalize": "ready" if (move_done or move_skipped) else "locked",
        }

        if active:
            state = steps.get(active)
            if state in ("ready", "running"):
                steps[active] = "running"

        return PipelineSnapshot(
            steps=steps,
            active_step_id=active,
            finalize_substate=finalize,
        )

    def set_active_step(self, step_id: str | None) -> None:
        self._active_step_id = step_id
        self.snapshot_changed.emit(
            self.build_snapshot(
                scan_done=False,
                duplicate_done=False,
                duplicate_skipped=False,
                move_done=False,
                move_skipped=False,
            )
        )

    def publish_run_progress(self, progress: PipelineRunProgress | None) -> None:
        self._run_progress = progress
        self.run_progress_changed.emit(progress)

    @property
    def run_progress(self) -> PipelineRunProgress | None:
        return self._run_progress
