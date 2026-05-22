"""Compose Qt stylesheets from design tokens."""

from types import ModuleType

from gui.styles import fonts
from gui.styles.theme_mode import ThemeMode
from gui.styles.tokens import colors_dark, colors_light


def _c(mode: ThemeMode) -> ModuleType:
    return colors_light if mode == ThemeMode.LIGHT else colors_dark


def get_stylesheet(mode: ThemeMode = ThemeMode.DARK) -> str:
    """Return full application stylesheet for the given theme."""
    t = _c(mode)
    ff = fonts.font_family_css()
    on_primary = "#121212" if mode == ThemeMode.DARK else "#FFFFFF"
    scroll_hover = "#4A4A4A" if mode == ThemeMode.DARK else "#BDBDBD"
    btn_secondary_hover_bg = t.HOVER

    return f"""
    QMainWindow {{
        background-color: {t.BG_BODY};
        color: {t.TEXT_PRIMARY};
    }}

    QWidget {{
        background-color: {t.BG_CONTAINER};
        color: {t.TEXT_PRIMARY};
        font-family: {ff};
        font-size: 14px;
    }}

    QWidget#header {{
        background-color: {t.SURFACE_ELEVATED};
        color: {t.TEXT_PRIMARY};
        padding: 24px 32px;
        border-bottom: 1px solid {t.BORDER_PRIMARY};
    }}

    QWidget#globalActionToolbar {{
        background-color: {t.SURFACE_ELEVATED};
        border-bottom: 1px solid {t.BORDER_PRIMARY};
    }}

    QWidget#workContextBar,
    QWidget#workCompactBar {{
        background: transparent;
    }}

    QWidget#wizardFooter {{
        background: transparent;
        border-top: 1px solid {t.BORDER_PRIMARY};
        padding-top: 8px;
    }}

    QWidget#workFileDock {{
        background: {t.BG_CONTAINER};
        border-top: 1px solid {t.BORDER_PRIMARY};
    }}

    QPushButton#workFileDockHeader {{
        text-align: left;
        padding: 8px 12px;
        color: {t.TEXT_SECONDARY};
        border: none;
        background: transparent;
    }}

    QPushButton#workFileDockHeader:hover {{
        color: {t.TEXT_PRIMARY};
        background: {t.HOVER};
    }}

    QWidget#pipelineRunConfirmSheet {{
        background: {t.BG_CONTAINER};
        border: 1px solid {t.BORDER_PRIMARY};
        border-radius: 8px;
    }}

    QPushButton#btnNeutral {{
        background-color: transparent;
        color: {t.TEXT_SECONDARY};
        border: 1px solid {t.BORDER_PRIMARY};
    }}

    QPushButton#btnNeutral:hover {{
        background-color: {t.HOVER};
        color: {t.TEXT_PRIMARY};
    }}

    QLabel#headerTitle {{
        font-size: 24px;
        font-weight: 700;
        color: {t.TEXT_PRIMARY};
    }}

    QLabel#statLabel {{
        font-size: 12px;
        color: {t.TEXT_SECONDARY};
    }}

    QLabel#statValue {{
        font-size: 20px;
        font-weight: 700;
        color: {t.PRIMARY};
    }}

    QWidget#statChip {{
        background-color: {t.BG_CONTAINER};
        border: 1px solid {t.BORDER_PRIMARY};
        border-radius: 8px;
        padding: 8px 12px;
    }}

    QWidget#sidebar {{
        background-color: {t.BG_SIDEBAR};
        border-right: 1px solid {t.BORDER_PRIMARY};
        padding: 16px;
    }}

    QLabel#navTitle {{
        font-size: 11px;
        font-weight: 700;
        color: {t.TEXT_DISABLED};
        letter-spacing: 0.5px;
    }}

    QToolButton#navSectionToggle {{
        border: none;
        color: {t.TEXT_SECONDARY};
        font-weight: 600;
        padding: 4px 0;
    }}

    QPushButton#navItem {{
        padding: 10px 12px;
        margin-bottom: 2px;
        border-radius: 6px;
        text-align: left;
        font-size: 13px;
        font-weight: 500;
        color: {t.TEXT_SECONDARY};
        background-color: transparent;
        border: none;
        border-left: 3px solid transparent;
    }}

    QPushButton#navItem:hover {{
        background-color: {t.HOVER};
        color: {t.TEXT_PRIMARY};
    }}

    QPushButton#navItem:checked {{
        background-color: {t.HOVER};
        color: {t.PRIMARY};
        border-left: 3px solid {t.PRIMARY};
    }}

    QPushButton {{
        padding: 12px 24px;
        border: none;
        border-radius: 6px;
        font-size: 14px;
        font-weight: 600;
        min-height: 20px;
    }}

    QPushButton#btnPrimary {{
        background-color: {t.PRIMARY};
        color: {on_primary};
    }}

    QPushButton#btnPrimary:hover {{
        background-color: {t.SECONDARY};
        color: {on_primary};
    }}

    QPushButton#btnPrimary:disabled {{
        background-color: {t.BORDER_PRIMARY};
        color: {t.TEXT_DISABLED};
    }}

    QPushButton#btnSecondary {{
        background-color: transparent;
        color: {t.TEXT_PRIMARY};
        border: 1px solid {t.BORDER_PRIMARY};
    }}

    QPushButton#btnSecondary:hover {{
        border-color: {t.PRIMARY};
        color: {t.PRIMARY};
        background-color: {btn_secondary_hover_bg};
    }}

    QPushButton#btnSuccess {{
        background-color: {t.COLOR_SUCCESS};
        color: {on_primary};
    }}

    QPushButton#btnDanger {{
        background-color: {t.COLOR_DANGER};
        color: {on_primary};
    }}

    QLineEdit, QTextEdit, QPlainTextEdit {{
        padding: 10px 14px;
        border: 1px solid {t.BORDER_PRIMARY};
        border-radius: 6px;
        background-color: {t.BG_INPUT};
        color: {t.TEXT_PRIMARY};
        font-size: 14px;
    }}

    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
        border-color: {t.PRIMARY};
    }}

    QComboBox {{
        padding: 10px 14px;
        border: 1px solid {t.BORDER_PRIMARY};
        border-radius: 6px;
        background-color: {t.BG_INPUT};
        color: {t.TEXT_PRIMARY};
        min-width: 120px;
    }}

    QComboBox:focus {{
        border-color: {t.PRIMARY};
    }}

    QComboBox QAbstractItemView {{
        background-color: {t.BG_CARD};
        border: 1px solid {t.BORDER_PRIMARY};
        color: {t.TEXT_PRIMARY};
        selection-background-color: {t.HOVER};
        selection-color: {t.PRIMARY};
    }}

    QCheckBox {{
        color: {t.TEXT_SECONDARY};
        spacing: 8px;
    }}

    QCheckBox::indicator {{
        width: 18px;
        height: 18px;
        border: 1px solid {t.BORDER_PRIMARY};
        border-radius: 4px;
        background-color: {t.BG_INPUT};
    }}

    QCheckBox::indicator:checked {{
        background-color: {t.PRIMARY};
        border-color: {t.PRIMARY};
    }}

    QProgressBar {{
        border: none;
        border-radius: 4px;
        background-color: {t.BORDER_PRIMARY};
        height: 8px;
    }}

    QProgressBar::chunk {{
        background-color: {t.PRIMARY};
        border-radius: 4px;
    }}

    QLabel {{
        color: {t.TEXT_PRIMARY};
        font-size: 14px;
    }}

    QLabel#pageTitle {{
        font-size: 20px;
        font-weight: 700;
        margin-bottom: 24px;
    }}

    QLabel#settingsTitle {{
        font-size: 18px;
        font-weight: 700;
        margin-bottom: 16px;
    }}

    QLabel#formLabel {{
        font-size: 14px;
        font-weight: 600;
        color: {t.TEXT_SECONDARY};
    }}

    QLabel#placeholder, QLabel#progressInfo, QLabel#formHint {{
        font-size: 13px;
        color: {t.TEXT_SECONDARY};
        padding: 4px 0;
    }}

    QWidget#statCard {{
        background-color: {t.BG_CARD};
        border: 1px solid {t.BORDER_PRIMARY};
        border-radius: 12px;
        padding: 16px;
    }}

    QWidget#statCard QLabel#statCardLabel {{
        font-size: 12px;
        color: {t.TEXT_SECONDARY};
    }}

    QWidget#statCard QLabel#statCardValue {{
        font-size: 22px;
        font-weight: 700;
        color: {t.PRIMARY};
    }}

    QWidget#statCard QLabel#statCardUnit {{
        font-size: 12px;
        color: {t.TEXT_SECONDARY};
    }}

    QListWidget#statsList {{
        background-color: {t.BG_INPUT};
        border: 1px solid {t.BORDER_PRIMARY};
        border-radius: 8px;
        color: {t.TEXT_PRIMARY};
    }}

    QPlainTextEdit#logConsole {{
        background-color: {t.BG_INPUT};
        border: 1px solid {t.BORDER_PRIMARY};
        color: {t.TEXT_PRIMARY};
        font-family: Consolas, monospace;
        font-size: 12px;
    }}

    QTextEdit#evidenceReason, QPlainTextEdit#evidenceJson {{
        background-color: {t.BG_INPUT};
        border: 1px solid {t.BORDER_PRIMARY};
        color: {t.TEXT_PRIMARY};
        font-family: Consolas, monospace;
        font-size: 12px;
    }}

    QWidget#pipelineStepper {{
        background: transparent;
    }}

    QLabel#pipelineStepConnector {{
        background-color: {t.BORDER_PRIMARY};
        max-height: 2px;
        min-height: 2px;
    }}

    QPushButton#pipelineStepCircle {{
        background-color: {t.BG_INPUT};
        color: {t.TEXT_SECONDARY};
        border: 2px solid {t.BORDER_PRIMARY};
        border-radius: 18px;
        font-size: 14px;
        font-weight: 700;
    }}

    QPushButton#pipelineStepCircle[active="true"] {{
        background-color: {t.PRIMARY};
        color: {on_primary};
        border-color: {t.PRIMARY};
    }}

    QWidget#pipelineStepNode[stepState="done"] QPushButton#pipelineStepCircle {{
        background-color: {t.COLOR_SUCCESS};
        color: {on_primary};
        border-color: {t.COLOR_SUCCESS};
    }}

    QWidget#pipelineStepNode[stepState="running"] QPushButton#pipelineStepCircle {{
        background-color: {t.PRIMARY};
        color: {on_primary};
        border-color: {t.PRIMARY};
    }}

    QLabel#pipelineStepTitle {{
        font-size: 14px;
        font-weight: 600;
        color: {t.TEXT_PRIMARY};
        background: transparent;
    }}

    QLabel#pipelineStepStatus {{
        font-size: 12px;
        color: {t.TEXT_SECONDARY};
        background: transparent;
    }}

    QWidget#pipelineStepStack {{
        background-color: {t.BG_CARD};
        border: 1px solid {t.BORDER_PRIMARY};
        border-radius: 12px;
    }}

    QWidget#pipelineProgressBlock {{
        background-color: {t.BG_INPUT};
        border: none;
        border-radius: 8px;
        padding: 12px;
    }}

    QWidget#pipelineFieldBlock {{
        background: transparent;
        border: none;
    }}

    QGroupBox {{
        background-color: {t.BG_CARD};
        border: 1px solid {t.BORDER_PRIMARY};
        border-radius: 12px;
        padding: 24px;
        margin-top: 10px;
        font-weight: 700;
    }}

    QGroupBox::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding: 0 8px;
        color: {t.TEXT_PRIMARY};
    }}

    QGroupBox QLabel {{
        background: transparent;
    }}

    QScrollBar:vertical {{
        border: none;
        background-color: {t.BORDER_PRIMARY};
        width: 12px;
    }}

    QScrollBar::handle:vertical {{
        background-color: {t.BORDER_SECONDARY};
        border-radius: 6px;
        min-height: 20px;
    }}

    QScrollBar::handle:vertical:hover {{
        background-color: {scroll_hover};
    }}

    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0;
    }}

    QScrollBar:horizontal {{
        border: none;
        background-color: {t.BORDER_PRIMARY};
        height: 12px;
    }}

    QScrollBar::handle:horizontal {{
        background-color: {t.BORDER_SECONDARY};
        border-radius: 6px;
        min-width: 20px;
    }}

    QSplitter::handle {{
        background-color: {t.BORDER_PRIMARY};
    }}
    """
