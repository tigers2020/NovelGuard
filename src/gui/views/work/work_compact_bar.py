"""Compact work bar: folder path, metrics, folder actions (no pipeline controls)."""

from typing import Optional

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from gui.view_models.work_dto import WorkSummary


class WorkCompactBar(QWidget):
    """Top of WorkTab wizard: folder + four metrics + folder/rescan only."""

    folder_change_requested = Signal()
    rescan_requested = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("workCompactBar")

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

    def update_summary(self, summary: WorkSummary, total_size_gb: float = 0.0) -> None:
        folder = summary.folder_path or "(미선택)"
        self._folder_label.setText(f"대상 폴더: {folder}")
        self._files_label.setText(f"파일 {summary.total_files:,}")
        self._size_label.setText(f"총 용량 {total_size_gb:.1f} GB")
        self._groups_label.setText(f"중복 그룹 {summary.duplicate_groups:,}")
        self._issues_label.setText(f"이슈 {summary.integrity_issues:,}")

    def set_actions_enabled(self, enabled: bool) -> None:
        self._folder_btn.setEnabled(enabled)
        self._rescan_btn.setEnabled(enabled)
