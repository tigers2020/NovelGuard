"""Collapsible section wrapper for WorkTab."""

from typing import Optional

from PySide6.QtWidgets import (
    QGroupBox,
    QVBoxLayout,
    QWidget,
)


class WorkSection(QGroupBox):
    """Checkable group box exposing section_id for scroll-to."""

    def __init__(
        self,
        section_id: str,
        title: str,
        *,
        expanded: bool = True,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(title, parent)
        self._section_id = section_id
        self.setObjectName(f"workSection_{section_id}")
        self.setCheckable(True)
        self.setChecked(expanded)

        self._body = QWidget()
        self._body_layout = QVBoxLayout(self._body)
        self._body_layout.setContentsMargins(0, 8, 0, 0)
        self._body_layout.setSpacing(12)

        outer = QVBoxLayout(self)
        outer.addWidget(self._body)

        self.toggled.connect(self._on_toggled)
        self._on_toggled(expanded)

    @property
    def section_id(self) -> str:
        return self._section_id

    @property
    def body_layout(self) -> QVBoxLayout:
        return self._body_layout

    def is_expanded(self) -> bool:
        return self.isChecked()

    def set_expanded(self, expanded: bool) -> None:
        self.setChecked(expanded)

    def _on_toggled(self, checked: bool) -> None:
        self._body.setVisible(checked)
