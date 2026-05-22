"""Wizard footer: prev/next, run pipeline, stop, global progress."""

from typing import Optional

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QProgressBar, QPushButton, QVBoxLayout, QWidget

from gui.view_models.work_pipeline_dto import STEP_ORDER, PipelineRunProgress


class WizardFooter(QWidget):
    """Footer: auto pipeline Primary, prev/next for step browse (rev. 3.9)."""

    prev_clicked = Signal()
    next_clicked = Signal()
    run_pipeline_requested = Signal()
    cancel_pipeline_requested = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("wizardFooter")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 12, 0, 0)
        layout.setSpacing(8)

        progress_row = QHBoxLayout()
        self._pipeline_label = QLabel("")
        self._pipeline_label.setObjectName("pipelineProgressLabel")
        progress_row.addWidget(self._pipeline_label, stretch=1)

        self._pipeline_bar = QProgressBar()
        self._pipeline_bar.setObjectName("pipelineProgress")
        self._pipeline_bar.setRange(0, 100)
        self._pipeline_bar.setValue(0)
        self._pipeline_bar.setVisible(False)
        progress_row.addWidget(self._pipeline_bar, stretch=2)
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

        actions.addStretch()

        self._run_btn = QPushButton("전체 작업 실행")
        self._run_btn.setObjectName("btnPrimary")
        self._run_btn.clicked.connect(self.run_pipeline_requested.emit)
        actions.addWidget(self._run_btn)

        self._cancel_btn = QPushButton("중지")
        self._cancel_btn.setObjectName("btnDanger")
        self._cancel_btn.clicked.connect(self.cancel_pipeline_requested.emit)
        self._cancel_btn.setVisible(False)
        actions.addWidget(self._cancel_btn)

        layout.addLayout(actions)

    def update_pipeline_progress(self, progress: PipelineRunProgress | None) -> None:
        if progress is None:
            self._pipeline_bar.setVisible(False)
            self._pipeline_label.setText("")
            return
        self._pipeline_bar.setVisible(True)
        self._pipeline_bar.setRange(0, 100)
        if progress.phase == "running":
            self._pipeline_bar.setValue(max(0, min(100, progress.overall_percent)))
        elif progress.phase == "awaiting_approval":
            self._pipeline_bar.setRange(0, 0)
        else:
            self._pipeline_bar.setValue(progress.overall_percent)
        step_no = progress.step_index + 1
        step_total = len(STEP_ORDER)
        self._pipeline_label.setText(
            f"{step_no}/{step_total} {progress.step_label} — {progress.detail_message}"
        )

    def set_pipeline_running(self, running: bool) -> None:
        """While running: hide Primary, show stop; prev/next stay enabled for browse."""
        self._run_btn.setVisible(not running)
        self._cancel_btn.setVisible(running)
        if not running:
            self._pipeline_bar.setVisible(False)
            self._pipeline_label.setText("")

    def set_run_enabled(self, enabled: bool) -> None:
        self._run_btn.setEnabled(enabled)

    def set_run_tooltip(self, text: str) -> None:
        self._run_btn.setToolTip(text)

    def set_prev_enabled(self, enabled: bool) -> None:
        self._prev_btn.setEnabled(enabled)

    def set_next_enabled(self, enabled: bool) -> None:
        self._next_btn.setEnabled(enabled)
