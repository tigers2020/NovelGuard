"""Tests for StepCard."""

from gui.views.work.step_card import StepCard


def test_step_card_active_property(qapp) -> None:
    card = StepCard("scan", "1", "스캔")
    card.set_active(True)
    assert card.property("active") == "true"


def test_step_card_state_label(qapp) -> None:
    card = StepCard("duplicate", "2", "중복 정리")
    card.set_state("running")
    assert card.state() == "running"
