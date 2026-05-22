"""Global Undo/Redo toolbar (shell until undo stack exists)."""

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QHBoxLayout,
    QStyle,
    QToolButton,
    QWidget,
)


class GlobalActionToolbar(QWidget):
    """Header-adjacent toolbar for undo/redo."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("globalActionToolbar")

        self.undo_action = QAction("실행 취소", self)
        self.undo_action.setObjectName("toolbarUndo")
        self.undo_action.setShortcut("Ctrl+Z")
        self.undo_action.setEnabled(False)
        self.undo_action.setToolTip("실행 취소 (미구현)")

        self.redo_action = QAction("다시 실행", self)
        self.redo_action.setObjectName("toolbarRedo")
        self.redo_action.setShortcut("Ctrl+Y")
        self.redo_action.setEnabled(False)
        self.redo_action.setToolTip("다시 실행 (미구현)")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(32, 8, 32, 8)
        layout.setSpacing(8)

        style = self.style()
        undo_btn = QToolButton(self)
        undo_btn.setDefaultAction(self.undo_action)
        undo_btn.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_ArrowBack))
        undo_btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        layout.addWidget(undo_btn)

        redo_btn = QToolButton(self)
        redo_btn.setDefaultAction(self.redo_action)
        redo_btn.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_ArrowForward))
        redo_btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        layout.addWidget(redo_btn)

        layout.addStretch()
