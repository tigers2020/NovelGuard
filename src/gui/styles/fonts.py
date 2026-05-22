"""Application font loading."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QFont, QFontDatabase

_FONT_DIR = Path(__file__).resolve().parent.parent / "resources" / "fonts"
_FALLBACK_FAMILIES = '"Noto Sans KR", "Segoe UI", sans-serif'


def _try_load_pretendard() -> str | None:
    candidates = [
        _FONT_DIR / "PretendardVariable.ttf",
        _FONT_DIR / "Pretendard-Regular.otf",
    ]
    for path in candidates:
        if not path.is_file():
            continue
        font_id = QFontDatabase.addApplicationFont(str(path))
        if font_id < 0:
            continue
        families = QFontDatabase.applicationFontFamilies(font_id)
        if families:
            return families[0]
    return None


def ui_font_family() -> str:
    """Primary UI font family name for QSS and QFont."""
    loaded = _try_load_pretendard()
    if loaded:
        return loaded
    return "Noto Sans KR"


def apply_application_font(app: object) -> None:
    """Set default application font from DESIGN typography body-md."""
    from PySide6.QtWidgets import QApplication

    if not isinstance(app, QApplication):
        return
    family = ui_font_family()
    font = QFont(family, 10)
    font.setStyleHint(QFont.StyleHint.SansSerif)
    app.setFont(font)


def font_family_css() -> str:
    """Quoted font-family list for stylesheets."""
    family = ui_font_family()
    return f'"{family}", {_FALLBACK_FAMILIES}'
