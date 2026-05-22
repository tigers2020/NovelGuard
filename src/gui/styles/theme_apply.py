"""Apply theme to running QApplication."""

from PySide6.QtWidgets import QApplication

from gui.styles.fonts import apply_application_font
from gui.styles.theme_mode import ThemeMode
from gui.styles.theme_registry import get_stylesheet


def apply_theme_to_app(mode: ThemeMode) -> None:
    """Set global stylesheet and font for the given theme mode."""
    instance = QApplication.instance()
    if instance is None or not isinstance(instance, QApplication):
        return
    apply_application_font(instance)
    instance.setStyleSheet(get_stylesheet(mode))
