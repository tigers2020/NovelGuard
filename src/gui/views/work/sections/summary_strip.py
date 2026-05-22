"""Work screen summary strip with section jump buttons."""

from typing import Callable, Optional

from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from gui.view_models.work_dto import WorkSummary


class SummaryStrip(QWidget):
    """Compact metrics and navigation to work sections."""

    def __init__(
        self,
        on_jump: Callable[[str], None],
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._on_jump = on_jump
        self.setObjectName("workSummaryStrip")

        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        self._folder_label = QLabel("폴더: (미선택)")
        self._folder_label.setObjectName("formLabel")
        layout.addWidget(self._folder_label)

        metrics_row = QHBoxLayout()
        self._files_label = QLabel("파일 0")
        self._groups_label = QLabel("그룹 0")
        self._saved_label = QLabel("절감 0.0 GB")
        self._issues_label = QLabel("이슈 0")
        for label in (
            self._files_label,
            self._groups_label,
            self._saved_label,
            self._issues_label,
        ):
            label.setObjectName("progressInfo")
            metrics_row.addWidget(label)
        metrics_row.addStretch()
        layout.addLayout(metrics_row)

        jump_row = QHBoxLayout()
        for section_id, text in (
            ("library", "라이브러리"),
            ("duplicate", "중복"),
            ("move", "이동"),
            ("quality", "품질"),
        ):
            btn = QPushButton(text)
            btn.setObjectName("btnSecondary")
            btn.clicked.connect(lambda _c=False, sid=section_id: self._on_jump(sid))
            jump_row.addWidget(btn)
        jump_row.addStretch()
        layout.addLayout(jump_row)

    def update_summary(self, summary: WorkSummary) -> None:
        folder = summary.folder_path or "(미선택)"
        self._folder_label.setText(f"폴더: {folder}")
        self._files_label.setText(f"파일 {summary.total_files:,}")
        self._groups_label.setText(f"그룹 {summary.duplicate_groups:,}")
        self._saved_label.setText(f"절감 {summary.saved_gb:.1f} GB")
        self._issues_label.setText(f"이슈 {summary.integrity_issues:,}")
