"""다크 테마 스타일시트."""
from .colors import (
    BG_BODY,
    BG_CONTAINER,
    BG_SIDEBAR,
    BG_CARD,
    BG_INPUT,
    PRIMARY_START,
    PRIMARY_END,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    TEXT_TERTIARY,
    TEXT_DISABLED,
    BORDER_PRIMARY,
    BORDER_SECONDARY,
    BORDER_ACCENT,
    COLOR_SUCCESS,
    COLOR_DANGER,
    COLOR_WARNING,
)


def get_dark_theme_stylesheet() -> str:
    """다크 테마 스타일시트 반환."""
    return f"""
    /* 메인 윈도우 */
    QMainWindow {{
        background-color: {BG_BODY};
        color: {TEXT_PRIMARY};
    }}
    
    /* 컨테이너 */
    QWidget {{
        background-color: {BG_CONTAINER};
        color: {TEXT_PRIMARY};
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Noto Sans KR', sans-serif;
        font-size: 14px;
    }}
    
    /* 헤더 */
    QWidget#header {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {PRIMARY_START}, stop:1 {PRIMARY_END});
        color: white;
        padding: 24px 32px;
        border-bottom: 1px solid {BORDER_PRIMARY};
    }}
    
    QLabel#headerTitle {{
        font-size: 28px;
        font-weight: 700;
        color: white;
    }}
    
    QLabel#statLabel {{
        font-size: 12px;
        opacity: 0.9;
        color: white;
    }}
    
    QLabel#statValue {{
        font-size: 20px;
        font-weight: 700;
        color: white;
    }}
    
    /* 사이드바 */
    QWidget#sidebar {{
        background-color: {BG_SIDEBAR};
        border-right: 1px solid {BORDER_PRIMARY};
        padding: 24px;
    }}
    
    QLabel#navTitle {{
        font-size: 12px;
        font-weight: 700;
        text-transform: uppercase;
        color: {TEXT_DISABLED};
        margin-bottom: 12px;
        letter-spacing: 0.5px;
    }}
    
    QPushButton#navItem {{
        padding: 12px 16px;
        margin-bottom: 4px;
        border-radius: 8px;
        text-align: left;
        font-size: 14px;
        font-weight: 500;
        color: {TEXT_SECONDARY};
        background-color: transparent;
        border: none;
    }}
    
    QPushButton#navItem:hover {{
        background-color: {BORDER_PRIMARY};
        color: {TEXT_PRIMARY};
    }}
    
    QPushButton#navItem:checked {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {PRIMARY_START}, stop:1 {PRIMARY_END});
        color: white;
    }}
    
    /* 버튼 */
    QPushButton {{
        padding: 12px 24px;
        border: none;
        border-radius: 8px;
        font-size: 14px;
        font-weight: 600;
        min-height: 20px;
    }}
    
    QPushButton#btnPrimary {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {PRIMARY_START}, stop:1 {PRIMARY_END});
        color: white;
    }}
    
    QPushButton#btnPrimary:hover {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {PRIMARY_END}, stop:1 {PRIMARY_START});
    }}
    
    QPushButton#btnSecondary {{
        background-color: {BORDER_PRIMARY};
        color: {TEXT_PRIMARY};
        border: 2px solid {BORDER_SECONDARY};
    }}
    
    QPushButton#btnSecondary:hover {{
        border-color: {PRIMARY_START};
        color: {PRIMARY_START};
        background-color: #252525;
    }}
    
    QPushButton#btnSuccess {{
        background-color: {COLOR_SUCCESS};
        color: white;
    }}
    
    QPushButton#btnSuccess:hover {{
        background-color: #218838;
    }}
    
    QPushButton#btnDanger {{
        background-color: {COLOR_DANGER};
        color: white;
    }}
    
    QPushButton#btnDanger:hover {{
        background-color: #c82333;
    }}
    
    /* 입력 필드 */
    QLineEdit, QTextEdit, QPlainTextEdit {{
        padding: 10px 14px;
        border: 2px solid {BORDER_PRIMARY};
        border-radius: 8px;
        background-color: {BG_INPUT};
        color: {TEXT_PRIMARY};
        font-size: 14px;
    }}
    
    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
        border-color: {PRIMARY_START};
    }}
    
    QLineEdit[readOnly="true"] {{
        background-color: {BORDER_PRIMARY};
        color: {TEXT_SECONDARY};
    }}
    
    /* 콤보박스 */
    QComboBox {{
        padding: 10px 14px;
        border: 2px solid {BORDER_PRIMARY};
        border-radius: 8px;
        background-color: {BG_INPUT};
        color: {TEXT_PRIMARY};
        font-size: 14px;
        min-width: 120px;
    }}
    
    QComboBox:focus {{
        border-color: {PRIMARY_START};
    }}
    
    QComboBox::drop-down {{
        border: none;
        width: 20px;
    }}
    
    QComboBox::down-arrow {{
        /* Qt 기본 화살표 사용 */
        width: 12px;
        height: 12px;
    }}
    
    QComboBox QAbstractItemView {{
        background-color: {BG_CARD};
        border: 1px solid {BORDER_PRIMARY};
        border-radius: 8px;
        color: {TEXT_PRIMARY};
        selection-background-color: {PRIMARY_START};
        selection-color: white;
    }}
    
    /* 체크박스 */
    QCheckBox {{
        color: {TEXT_SECONDARY};
        font-size: 14px;
        spacing: 8px;
    }}
    
    QCheckBox::indicator {{
        width: 18px;
        height: 18px;
        border: 2px solid {BORDER_PRIMARY};
        border-radius: 4px;
        background-color: {BG_INPUT};
    }}
    
    QCheckBox::indicator:hover {{
        border-color: {PRIMARY_START};
    }}
    
    QCheckBox::indicator:checked {{
        background-color: {PRIMARY_START};
        border-color: {PRIMARY_START};
        /* Qt 기본 체크 표시 사용 */
    }}
    
    /* 프로그레스 바 */
    QProgressBar {{
        border: none;
        border-radius: 4px;
        background-color: {BORDER_PRIMARY};
        height: 8px;
        text-align: left;
    }}
    
    QProgressBar::chunk {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {PRIMARY_START}, stop:1 {PRIMARY_END});
        border-radius: 4px;
    }}
    
    /* 레이블 */
    QLabel {{
        color: {TEXT_PRIMARY};
        font-size: 14px;
    }}
    
    QLabel#pageTitle {{
        font-size: 24px;
        font-weight: 700;
        color: {TEXT_PRIMARY};
        margin-bottom: 24px;
    }}
    
    QLabel#settingsTitle {{
        font-size: 18px;
        font-weight: 700;
        color: {TEXT_PRIMARY};
        margin-bottom: 16px;
    }}
    
    QLabel#formLabel {{
        font-size: 14px;
        font-weight: 600;
        color: {TEXT_SECONDARY};
        margin-bottom: 8px;
    }}
    
    /* 그룹 박스 */
    QGroupBox {{
        background-color: {BG_CARD};
        border: 1px solid {BORDER_PRIMARY};
        border-radius: 12px;
        padding: 24px;
        margin-top: 10px;
        font-size: 18px;
        font-weight: 700;
        color: {TEXT_PRIMARY};
    }}
    
    QGroupBox::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding: 0 8px;
        color: {TEXT_PRIMARY};
    }}
    
    /* 그룹 박스 내부 레이블은 투명하게 */
    QGroupBox QLabel {{
        background: transparent;
    }}
    
    /* 스크롤바 */
    QScrollBar:vertical {{
        border: none;
        background-color: {BORDER_PRIMARY};
        width: 12px;
        margin: 0;
    }}
    
    QScrollBar::handle:vertical {{
        background-color: {BORDER_SECONDARY};
        border-radius: 6px;
        min-height: 20px;
    }}
    
    QScrollBar::handle:vertical:hover {{
        background-color: #4a4a4a;
    }}
    
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0;
    }}
    
    QScrollBar:horizontal {{
        border: none;
        background-color: {BORDER_PRIMARY};
        height: 12px;
        margin: 0;
    }}
    
    QScrollBar::handle:horizontal {{
        background-color: {BORDER_SECONDARY};
        border-radius: 6px;
        min-width: 20px;
    }}
    
    QScrollBar::handle:horizontal:hover {{
        background-color: #4a4a4a;
    }}
    
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
        width: 0;
    }}
    
    /* 스플리터 */
    QSplitter::handle {{
        background-color: {BORDER_PRIMARY};
    }}
    
    QSplitter::handle:horizontal {{
        width: 1px;
    }}
    
    QSplitter::handle:vertical {{
        height: 1px;
    }}
    """
