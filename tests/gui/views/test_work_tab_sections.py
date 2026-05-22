"""WorkTab stepper + stacked panel smoke tests."""

from gui.models.app_state import AppState
from gui.views.work.work_tab import WorkTab


def test_work_tab_has_four_stacked_steps(qapp) -> None:
    tab = WorkTab(app_state=AppState())
    assert tab._step_stack.count() == 4


def test_work_tab_stepper_switches_stack(qapp) -> None:
    tab = WorkTab(app_state=AppState())
    tab.set_active_step("move")
    assert tab._step_stack.currentIndex() == 2
    assert tab._stepper._steps["move"]._circle.property("active") == "true"
