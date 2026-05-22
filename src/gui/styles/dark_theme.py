"""Dark theme stylesheet (compat shim)."""

from gui.styles.theme_mode import ThemeMode
from gui.styles.theme_registry import get_stylesheet


def get_dark_theme_stylesheet() -> str:
    """Return dark theme stylesheet."""
    return get_stylesheet(ThemeMode.DARK)
