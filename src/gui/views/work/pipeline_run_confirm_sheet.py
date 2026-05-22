"""One-shot approval panel before auto pipeline run (rev. 3.2)."""

from typing import Optional

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from gui.services.pipeline_run_preview import PipelineRunPreview


class PipelineRunConfirmSheet(QWidget):
    """Non-modal summary + destructive-work checkbox before pipeline start."""

    confirmed = Signal()
    cancelled = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("pipelineRunConfirmSheet")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        title = QLabel("전체 작업 실행 확인")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        self._folder_label = QLabel()
        self._folder_label.setObjectName("formLabel")
        self._folder_label.setWordWrap(True)
        layout.addWidget(self._folder_label)

        self._summary_label = QLabel()
        self._summary_label.setObjectName("formHint")
        self._summary_label.setWordWrap(True)
        layout.addWidget(self._summary_label)

        self._error_label = QLabel()
        self._error_label.setObjectName("formHint")
        self._error_label.setWordWrap(True)
        self._error_label.setVisible(False)
        layout.addWidget(self._error_label)

        self._confirm_check = QCheckBox("파괴적 작업(이동·삭제)의 결과를 확인했으며 실행합니다")
        self._confirm_check.setObjectName("pipelineConfirmCheck")
        self._confirm_check.toggled.connect(self._on_check_toggled)
        layout.addWidget(self._confirm_check)

        layout.addStretch()

        actions = QHBoxLayout()
        actions.addStretch()
        self._cancel_btn = QPushButton("취소")
        self._cancel_btn.setObjectName("btnSecondary")
        self._cancel_btn.clicked.connect(self.cancelled.emit)
        actions.addWidget(self._cancel_btn)

        self._start_btn = QPushButton("시작")
        self._start_btn.setObjectName("btnPrimary")
        self._start_btn.setEnabled(False)
        self._start_btn.clicked.connect(self._on_start_clicked)
        actions.addWidget(self._start_btn)
        layout.addLayout(actions)

    def set_preview(self, preview: PipelineRunPreview) -> None:
        """Fill labels from pre-flight preview."""
        self._error_label.setVisible(False)
        folder = preview.folder_path or "(미선택)"
        self._folder_label.setText(f"대상 폴더: {folder}")
        self._summary_label.setText(
            f"파일 {preview.total_files:,}건 · 중복 그룹 {preview.duplicate_groups:,}개 · "
            f"중복 이동 예상 {preview.duplicate_move_count:,}건 · "
            f"정리 이동/복사 예상 {preview.organize_dry_run_total:,}건"
        )
        if preview.error_message:
            self.show_error(preview.error_message)
        self._confirm_check.setChecked(False)
        self._start_btn.setEnabled(False)

    def show_error(self, message: str) -> None:
        """Show pre-flight error; start stays disabled."""
        self._error_label.setText(message)
        self._error_label.setVisible(True)
        self._start_btn.setEnabled(False)

    def is_confirmed(self) -> bool:
        return self._confirm_check.isChecked()

    def _on_check_toggled(self, checked: bool) -> None:
        has_error = self._error_label.isVisible() and bool(self._error_label.text())
        self._start_btn.setEnabled(checked and not has_error)

    def _on_start_clicked(self) -> None:
        if self.is_confirmed() and self._start_btn.isEnabled():
            self.confirmed.emit()
