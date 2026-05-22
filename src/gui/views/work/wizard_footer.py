"""Wizard footer: prev/next, step execute, stop, summary."""

from typing import Optional

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QProgressBar, QPushButton, QVBoxLayout, QWidget


class WizardFooter(QWidget):
    """Footer controls for the work pipeline (step-only execution, rev. 3.3)."""

    prev_clicked = Signal()
    next_clicked = Signal()
    execute_step_requested = Signal()
    cancel_step_requested = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("wizardFooter")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 12, 0, 0)
        layout.setSpacing(8)

        progress_row = QHBoxLayout()
        self._progress_label = QLabel("")
        self._progress_label.setObjectName("pipelineProgressLabel")
        progress_row.addWidget(self._progress_label, stretch=1)

        self._progress_bar = QProgressBar()
        self._progress_bar.setObjectName("pipelineProgress")
        self._progress_bar.setRange(0, 0)
        self._progress_bar.setVisible(False)
        progress_row.addWidget(self._progress_bar, stretch=2)
        layout.addLayout(progress_row)

        actions = QHBoxLayout()
        self._prev_btn = QPushButton("◀ 이전")
        self._prev_btn.setObjectName("btnSecondary")
        self._prev_btn.clicked.connect(self.prev_clicked.emit)
        actions.addWidget(self._prev_btn)

        self._next_btn = QPushButton("다음 ▶")
        self._next_btn.setObjectName("btnSecondary")
        self._next_btn.clicked.connect(self.next_clicked.emit)
        actions.addWidget(self._next_btn)

        self._summary_label = QLabel("")
        self._summary_label.setObjectName("footerSummary")
        actions.addWidget(self._summary_label, stretch=1)

        self._execute_btn = QPushButton("현재 단계 실행")
        self._execute_btn.setObjectName("btnPrimary")
        self._execute_btn.clicked.connect(self.execute_step_requested.emit)
        actions.addWidget(self._execute_btn)

        self._cancel_btn = QPushButton("중지")
        self._cancel_btn.setObjectName("btnDanger")
        self._cancel_btn.clicked.connect(self.cancel_step_requested.emit)
        self._cancel_btn.setVisible(False)
        actions.addWidget(self._cancel_btn)

        layout.addLayout(actions)

    def set_summary(self, text: str) -> None:
        self._summary_label.setText(text)

    def set_execute_label(self, label: str) -> None:
        self._execute_btn.setText(label)

    def set_execute_enabled(self, enabled: bool) -> None:
        self._execute_btn.setEnabled(enabled)

    def set_step_running(self, running: bool) -> None:
        self._execute_btn.setVisible(not running)
        self._cancel_btn.setVisible(running)
        self._prev_btn.setEnabled(not running)
        self._next_btn.setEnabled(not running)
        self._progress_bar.setVisible(running)
        if not running:
            self._progress_bar.setRange(0, 0)
            self._progress_label.setText("")

    def set_step_progress(self, message: str, indeterminate: bool = True) -> None:
        self._progress_label.setText(message)
        if indeterminate:
            self._progress_bar.setRange(0, 0)
        else:
            self._progress_bar.setRange(0, 100)

    def set_prev_enabled(self, enabled: bool) -> None:
        if self._cancel_btn.isVisible():
            return
        self._prev_btn.setEnabled(enabled)

    def set_next_enabled(self, enabled: bool) -> None:
        if self._cancel_btn.isVisible():
            return
        self._next_btn.setEnabled(enabled)
