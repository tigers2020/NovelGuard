"""Resolve AppState / MainWindow from widget parent chain."""

from typing import TYPE_CHECKING, Optional, cast

from PySide6.QtWidgets import QWidget

from gui.models.app_state import AppState

if TYPE_CHECKING:
    from gui.views.main_window import MainWindow


def get_app_state(widget: QWidget) -> AppState:
    parent: Optional[QWidget] = widget
    while parent is not None:
        if hasattr(parent, "_app_state"):
            return cast(AppState, getattr(parent, "_app_state"))
        parent = parent.parent()  # type: ignore[assignment]
    return AppState()


def get_main_window(widget: QWidget) -> Optional["MainWindow"]:
    parent: Optional[QWidget] = widget
    while parent is not None:
        if parent.__class__.__name__ == "MainWindow":
            return parent  # type: ignore[return-value]
        parent = parent.parent()  # type: ignore[assignment]
    return None


def get_settings_tab(widget: QWidget):
    main = get_main_window(widget)
    if main is not None and hasattr(main, "_get_settings_tab"):
        return main._get_settings_tab()
    return None
