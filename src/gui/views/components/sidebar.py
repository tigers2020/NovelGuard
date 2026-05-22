"""사이드바 컴포넌트 (네비게이션 메뉴)."""

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QPushButton,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from gui.styles.icon_registry import nav_icon


class SidebarWidget(QWidget):
    """사이드바 위젯 - 네비게이션 메뉴."""

    tab_changed = Signal(str)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(228)

        self._button_group = QButtonGroup(self)
        self._button_group.setExclusive(True)
        self._section_bodies: list[QWidget] = []

        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        layout.addLayout(
            self._create_collapsible_section(
                "메인 작업",
                [
                    ("scan", "파일 스캔"),
                    ("duplicate", "중복 정리"),
                    ("move_organize", "이동 정리"),
                    ("small", "작은 파일"),
                    ("integrity", "무결성"),
                    ("encoding", "인코딩"),
                ],
            )
        )
        layout.addLayout(
            self._create_collapsible_section(
                "도구",
                [
                    ("stats", "통계"),
                ],
            )
        )
        layout.addLayout(
            self._create_collapsible_section(
                "시스템",
                [
                    ("logs", "작업 로그"),
                    ("undo", "Undo"),
                    ("settings", "설정"),
                ],
            )
        )
        layout.addStretch()

    def _create_collapsible_section(self, title: str, items: list[tuple[str, str]]) -> QVBoxLayout:
        section_layout = QVBoxLayout()
        section_layout.setSpacing(6)

        header_row = QWidget()
        header_layout = QVBoxLayout(header_row)
        header_layout.setContentsMargins(0, 0, 0, 0)

        toggle = QToolButton()
        toggle.setObjectName("navSectionToggle")
        toggle.setText(f"▼ {title}")
        toggle.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        toggle.setCheckable(True)
        toggle.setChecked(True)
        toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        header_layout.addWidget(toggle)

        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(0, 4, 0, 0)
        body_layout.setSpacing(2)

        for tab_name, label in items:
            nav_button = self._create_nav_button(tab_name, label)
            self._button_group.addButton(nav_button)
            body_layout.addWidget(nav_button)
            if tab_name == "scan":
                nav_button.setChecked(True)

        def _on_toggle(checked: bool) -> None:
            body.setVisible(checked)
            toggle.setText(f"{'▼' if checked else '▶'} {title}")

        toggle.toggled.connect(_on_toggle)
        _on_toggle(True)

        section_layout.addWidget(header_row)
        section_layout.addWidget(body)
        self._section_bodies.append(body)
        return section_layout

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
