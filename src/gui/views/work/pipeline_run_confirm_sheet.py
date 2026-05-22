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

        self._integrity_hint = QLabel(
            "무결성 검사 후, 백업(.novelguard.bak)을 남기고 "
            "변환 가능한 비 UTF-8 파일을 UTF-8로 자동 변환합니다."
        )
        self._integrity_hint.setObjectName("formHint")
        self._integrity_hint.setWordWrap(True)
        layout.addWidget(self._integrity_hint)

        self._start_hint = QLabel("위 확인란을 체크하면 시작할 수 있습니다.")
        self._start_hint.setObjectName("formHint")
        layout.addWidget(self._start_hint)

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
        groups_part = f"중복 그룹 {preview.duplicate_groups:,}개"
        if preview.duplicate_groups_from_cache:
            ts = preview.cached_detection_timestamp or ""
            date_hint = ts[:10] if len(ts) >= 10 else "마지막 탐지"
            groups_part = f"{groups_part} ({date_hint} 탐지 기준)"
        self._summary_label.setText(
            f"파일 {preview.total_files:,}건 · {groups_part} · "
            f"중복 이동 예상 {preview.duplicate_move_count:,}건 · "
            f"정리 이동/복사 예상 {preview.organize_dry_run_total:,}건"
        )
        if preview.error_message:
            self.show_error(preview.error_message)
        else:
            self._error_label.clear()
            self._error_label.setVisible(False)
        self._confirm_check.setChecked(False)
        self._update_start_state()

    def show_error(self, message: str) -> None:
        """Show pre-flight error; start stays disabled."""
        self._error_label.setText(message)
        self._error_label.setVisible(True)
        self._update_start_state()

    def is_confirmed(self) -> bool:
        return self._confirm_check.isChecked()

    def _has_blocking_error(self) -> bool:
        return self._error_label.isVisible() and bool(self._error_label.text().strip())

    def _update_start_state(self) -> None:
        can_start = self._confirm_check.isChecked() and not self._has_blocking_error()
        self._start_btn.setEnabled(can_start)
        self._start_hint.setVisible(not can_start and not self._has_blocking_error())
        if can_start:
            self._start_btn.setToolTip("")
        elif self._has_blocking_error():
            self._start_btn.setToolTip("오류를 해결한 뒤 다시 시도하세요.")
        else:
            self._start_btn.setToolTip("위 확인란을 체크하면 시작할 수 있습니다.")

    def _on_check_toggled(self, _checked: bool) -> None:
        self._update_start_state()

    def _on_start_clicked(self) -> None:
        if self.is_confirmed() and self._start_btn.isEnabled():
            self.confirmed.emit()
