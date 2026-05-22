"""Tests for WizardFooter."""

from gui.views.work.wizard_footer import WizardFooter


def test_footer_run_emits(qapp) -> None:
    footer = WizardFooter()
    got: list[bool] = []
    footer.run_pipeline_requested.connect(lambda: got.append(True))
    footer._run_btn.click()
    assert got
