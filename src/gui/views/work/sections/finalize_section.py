"""Finalize step: apply remaining work and auto integrity check."""

import logging
from typing import Optional

from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

logger = logging.getLogger(__name__)


class FinalizeSection(QWidget):
    """Apply + integrity auto-run (integrity port optional)."""

    apply_succeeded = None  # placeholder; wired when apply use case exists

    def __init__(self, parent: Optional[QWidget] = None, log_sink=None) -> None:
        super().__init__(parent)
        self._log_sink = log_sink
        layout = QVBoxLayout(self)

        bar = QHBoxLayout()
        self._apply_btn = QPushButton("적용하기")
        self._apply_btn.setObjectName("btnPrimary")
        self._apply_btn.clicked.connect(self._on_apply_clicked)
        bar.addWidget(self._apply_btn)

        for label in ("인코딩 분석", "UTF-8 변환"):
            btn = QPushButton(label)
            btn.setObjectName("btnSecondary")
            btn.setEnabled(False)
            btn.setToolTip("미구현")
            bar.addWidget(btn)
        bar.addStretch()
        layout.addLayout(bar)

        self._status_label = QLabel("이동·중복 적용이 완료되면 적용 및 무결성 검사를 진행합니다.")
        self._status_label.setObjectName("progressInfo")
        layout.addWidget(self._status_label)

        self._progress_bar = QProgressBar()
        self._progress_bar.setMaximumWidth(400)
        self._progress_bar.setVisible(False)
        layout.addWidget(self._progress_bar)

        hint = QLabel("작은 파일 정리: 준비 중")
        hint.setObjectName("formHint")
        layout.addWidget(hint)

    def _on_apply_clicked(self) -> None:
        self._status_label.setText(
            "적용 use case 미연결 — 파이프라인에서 무결성 단계로 진행합니다."
        )

    def run_apply_and_integrity_auto(self, parent: QWidget) -> bool:
        """Pipeline hook: apply (stub) then auto integrity."""
        self._status_label.setText("적용 완료 · 무결성 검사 중...")
        self._progress_bar.setVisible(True)
        self._progress_bar.setRange(0, 0)
        self._progress_bar.setValue(0)
        self._finish_integrity_noop()
        return True

    def _finish_integrity_noop(self) -> None:
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(100)
        self._status_label.setText("적용 ✓ · 무결성 검사 (미구현)")
        logger.info("integrity check skipped: port not wired")
