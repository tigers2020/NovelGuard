"""Tests for WizardFooter."""

from gui.views.work.wizard_footer import WizardFooter


def test_footer_execute_emits(qapp) -> None:
    footer = WizardFooter()
    got: list[bool] = []
    footer.execute_step_requested.connect(lambda: got.append(True))
    footer._execute_btn.click()
    assert got


def test_footer_step_running_toggles_buttons(qapp) -> None:
    footer = WizardFooter()
    footer.show()
    footer.set_step_running(True)
    assert not footer._cancel_btn.isHidden()
    assert footer._execute_btn.isHidden()
    footer.set_step_running(False)
    assert not footer._execute_btn.isHidden()
    assert footer._cancel_btn.isHidden()
