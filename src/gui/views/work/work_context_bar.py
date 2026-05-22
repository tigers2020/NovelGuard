"""Work screen context: folder, metrics, and global pipeline progress."""

from typing import Optional

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from gui.view_models.work_dto import WorkSummary
from gui.view_models.work_pipeline_dto import STEP_ORDER, PipelineRunProgress


class WorkContextBar(QWidget):
    """Top bar on WorkTab: folder, metrics, run pipeline, global progress."""

    run_pipeline_requested = Signal()
    cancel_pipeline_requested = Signal()
    folder_change_requested = Signal()
    rescan_requested = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("workContextBar")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        folder_row = QHBoxLayout()
        self._folder_label = QLabel("대상 폴더: (미선택)")
        self._folder_label.setObjectName("formLabel")
        folder_row.addWidget(self._folder_label, stretch=1)

        self._folder_btn = QPushButton("폴더 변경")
        self._folder_btn.setObjectName("btnNeutral")
        self._folder_btn.clicked.connect(self.folder_change_requested.emit)
        folder_row.addWidget(self._folder_btn)

        self._rescan_btn = QPushButton("재스캔")
        self._rescan_btn.setObjectName("btnSecondary")
        self._rescan_btn.clicked.connect(self.rescan_requested.emit)
        folder_row.addWidget(self._rescan_btn)
        layout.addLayout(folder_row)

        metrics_row = QHBoxLayout()
        self._files_label = QLabel("파일 0")
        self._size_label = QLabel("총 용량 0.0 GB")
        self._groups_label = QLabel("중복 그룹 0")
        self._issues_label = QLabel("이슈 0")
        for label in (
            self._files_label,
            self._size_label,
            self._groups_label,
            self._issues_label,
        ):
            label.setObjectName("progressInfo")
            metrics_row.addWidget(label)
        metrics_row.addStretch()
        layout.addLayout(metrics_row)

        pipeline_row = QHBoxLayout()
        self._run_btn = QPushButton("전체 작업 실행")
        self._run_btn.setObjectName("btnPrimary")
        self._run_btn.clicked.connect(self.run_pipeline_requested.emit)
        pipeline_row.addWidget(self._run_btn)

        self._cancel_btn = QPushButton("중지")
        self._cancel_btn.setObjectName("btnDanger")
        self._cancel_btn.clicked.connect(self.cancel_pipeline_requested.emit)
        self._cancel_btn.setVisible(False)
        pipeline_row.addWidget(self._cancel_btn)

        self._pipeline_bar = QProgressBar()
        self._pipeline_bar.setObjectName("pipelineProgress")
        self._pipeline_bar.setRange(0, 100)
        self._pipeline_bar.setValue(0)
        self._pipeline_bar.setVisible(False)
        pipeline_row.addWidget(self._pipeline_bar, stretch=1)

        self._pipeline_label = QLabel("")
        self._pipeline_label.setObjectName("pipelineProgressLabel")
        pipeline_row.addWidget(self._pipeline_label)
        layout.addLayout(pipeline_row)

    def update_summary(self, summary: WorkSummary, total_size_gb: float = 0.0) -> None:
        folder = summary.folder_path or "(미선택)"
        self._folder_label.setText(f"대상 폴더: {folder}")
        self._files_label.setText(f"파일 {summary.total_files:,}")
        self._size_label.setText(f"총 용량 {total_size_gb:.1f} GB")
        self._groups_label.setText(f"중복 그룹 {summary.duplicate_groups:,}")
        self._issues_label.setText(f"이슈 {summary.integrity_issues:,}")

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
        self._run_btn.setEnabled(not running)
        self._cancel_btn.setVisible(running)
        self._folder_btn.setEnabled(not running)
        if not running:
            self._pipeline_bar.setVisible(False)
            self._pipeline_label.setText("")
