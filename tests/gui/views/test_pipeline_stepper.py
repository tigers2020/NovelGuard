"""Tests for PipelineStepper."""

from gui.views.work.pipeline_stepper import PipelineStepper


def test_stepper_emits_click_when_enabled(qapp) -> None:
    stepper = PipelineStepper()
    stepper.set_step_state("scan", "ready")
    received: list[str] = []
    stepper.step_clicked.connect(received.append)
    stepper._steps["scan"]._circle.click()
    assert received == ["scan"]
