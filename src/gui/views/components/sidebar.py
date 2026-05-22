"""사이드바 컴포넌트 (네비게이션 메뉴)."""

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from gui.styles.icon_registry import nav_icon


class SidebarWidget(QWidget):
    """사이드바 — 작업 · 로그 · 설정."""

    tab_changed = Signal(str)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(228)

        self._button_group = QButtonGroup(self)
        self._button_group.setExclusive(True)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        for tab_name, label in (
            ("work", "작업"),
            ("logs", "로그"),
            ("settings", "설정"),
        ):
            nav_button = self._create_nav_button(tab_name, label)
            self._button_group.addButton(nav_button)
            layout.addWidget(nav_button)
            if tab_name == "work":
                nav_button.setChecked(True)

        layout.addStretch()

    def _create_nav_button(self, tab_name: str, label: str) -> QPushButton:
        button = QPushButton(label)
        button.setObjectName("navItem")
        button.setIcon(nav_icon(self, tab_name))
        button.setCheckable(True)
        button.setFlat(True)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setProperty("tab_name", tab_name)
        button.clicked.connect(lambda _checked=False, name=tab_name: self._on_tab_clicked(name))
        return button

    def _on_tab_clicked(self, tab_name: str) -> None:
        self.tab_changed.emit(tab_name)

    def set_active_tab(self, tab_name: str) -> None:
        for button in self._button_group.buttons():
            if button.property("tab_name") == tab_name:
                button.setChecked(True)
                break
