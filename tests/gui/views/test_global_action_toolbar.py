"""Tests for GlobalActionToolbar."""

from PySide6.QtWidgets import QWidget

from gui.views.components.global_action_toolbar import GlobalActionToolbar


def test_toolbar_undo_redo_disabled_by_default(qapp) -> None:
    parent = QWidget()
    bar = GlobalActionToolbar(parent)
    assert not bar.undo_action.isEnabled()
    assert not bar.redo_action.isEnabled()
    assert "미구현" in bar.undo_action.toolTip()
