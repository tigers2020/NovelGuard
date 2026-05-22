"""Tests for WizardFooter."""

from gui.views.work.wizard_footer import WizardFooter


def test_footer_run_pipeline_emits(qapp) -> None:
    footer = WizardFooter()
    got: list[bool] = []
    footer.run_pipeline_requested.connect(lambda: got.append(True))
    footer._run_btn.click()
    assert got


def test_footer_pipeline_running_hides_run_shows_cancel(qapp) -> None:
    footer = WizardFooter()
    footer.show()
    footer.set_pipeline_running(True)
    assert footer._run_btn.isHidden()
    assert not footer._cancel_btn.isHidden()
    footer.set_pipeline_running(False)
    assert not footer._run_btn.isHidden()
