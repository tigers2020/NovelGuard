"""Collapsible file list dock at the bottom of WorkTab."""

from typing import Optional

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QPushButton, QSplitter, QVBoxLayout, QWidget


class WorkFileDock(QWidget):
    """Hosts FileListTableWidget with a toggle header; default collapsed."""

    expand_requested = Signal()
    collapsed_changed = Signal(bool)

    _COLLAPSED_HEIGHT = 48

    def __init__(self, table_widget: QWidget, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("workFileDock")
        self._table = table_widget
        self._splitter: Optional[QSplitter] = None
        self._collapsed = True
        self._file_count = 0

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._toggle_btn = QPushButton("▼ 파일 목록 (0)")
        self._toggle_btn.setObjectName("workFileDockHeader")
        self._toggle_btn.setFlat(True)
        self._toggle_btn.clicked.connect(self._on_toggle)
        layout.addWidget(self._toggle_btn)

        layout.addWidget(self._table, stretch=1)
        self._table.setVisible(False)

    def bind_splitter(self, splitter: QSplitter) -> None:
        """Parent vertical splitter (wizard pane + this dock)."""
        self._splitter = splitter

    def is_collapsed(self) -> bool:
        return self._collapsed

    def set_file_count(self, count: int) -> None:
        self._file_count = count
        arrow = "▼" if self._collapsed else "▲"
        self._toggle_btn.setText(f"{arrow} 파일 목록 ({count:,})")

    def collapse(self) -> None:
        self._collapsed = True
        self._table.setVisible(False)
        self.set_file_count(self._file_count)
        if self._splitter is not None:
            total = max(sum(self._splitter.sizes()), 1)
            self._splitter.setSizes([total - self._COLLAPSED_HEIGHT, self._COLLAPSED_HEIGHT])
        self.collapsed_changed.emit(True)

    def expand(self) -> None:
        self._collapsed = False
        self._table.setVisible(True)
        self.set_file_count(self._file_count)
        if self._splitter is not None:
            total = max(sum(self._splitter.sizes()), 800)
            self._splitter.setSizes([int(total * 0.75), int(total * 0.25)])
        self.expand_requested.emit()
        self.collapsed_changed.emit(False)

    def _on_toggle(self) -> None:
        if self._collapsed:
            self.expand()
        else:
            self.collapse()
