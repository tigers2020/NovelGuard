"""Tests for WorkContextBar."""

from gui.views.work.work_context_bar import WorkContextBar


def test_context_bar_run_button_emits_signal(qapp) -> None:
    bar = WorkContextBar()
    received: list[bool] = []
    bar.run_pipeline_requested.connect(lambda: received.append(True))
    bar._run_btn.click()
    assert len(received) == 1
