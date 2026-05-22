"""Finalize step: apply remaining work and auto integrity check."""

import logging
from typing import Callable, Optional

from PySide6.QtCore import QEventLoop
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from gui.view_models.integrity_view_model import IntegrityViewModel

logger = logging.getLogger(__name__)


class FinalizeSection(QWidget):
    """Apply + integrity auto-run + optional UTF-8 conversion."""

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        log_sink=None,
        integrity_view_model: Optional[IntegrityViewModel] = None,
        on_stats_refresh: Optional[Callable[[], None]] = None,
    ) -> None:
        super().__init__(parent)
        self._log_sink = log_sink
        self._vm = integrity_view_model
        self._on_stats_refresh = on_stats_refresh
        self._flow_ok = False

        layout = QVBoxLayout(self)

        tools = QHBoxLayout()
        self._btn_analyze = QPushButton("인코딩 분석")
        self._btn_analyze.setObjectName("btnSecondary")
        self._btn_utf8 = QPushButton("UTF-8 변환")
        self._btn_utf8.setObjectName("btnSecondary")
        tools.addWidget(self._btn_analyze)
        tools.addWidget(self._btn_utf8)
        tools.addStretch()
        layout.addLayout(tools)

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
        layout.addStretch()

        self._btn_analyze.clicked.connect(self._on_analyze_clicked)
        self._btn_utf8.clicked.connect(self._on_utf8_clicked)
        self._update_button_state()

        if self._vm:
            self._vm.status_message.connect(self._status_label.setText)
            self._vm.progress_changed.connect(self._on_progress)
            self._vm.finalize_flow_completed.connect(self._on_finalize_flow_completed)
            self._vm.finalize_flow_failed.connect(self._on_finalize_flow_failed)
            self._vm.integrity_only_completed.connect(self._on_integrity_only_completed)

    def set_integrity_view_model(self, vm: IntegrityViewModel) -> None:
        self._vm = vm
        vm.status_message.connect(self._status_label.setText)
        vm.progress_changed.connect(self._on_progress)
        vm.finalize_flow_completed.connect(self._on_finalize_flow_completed)
        vm.finalize_flow_failed.connect(self._on_finalize_flow_failed)
        vm.integrity_only_completed.connect(self._on_integrity_only_completed)
        self._update_button_state()

    def refresh_button_state(self) -> None:
        self._update_button_state()

    def _update_button_state(self) -> None:
        enabled = self._vm is not None and self._vm.has_files
        self._btn_analyze.setEnabled(enabled)
        self._btn_utf8.setEnabled(enabled)
        if enabled:
            self._btn_analyze.setToolTip("")
            self._btn_utf8.setToolTip("")
        else:
            tip = "스캔 후 사용 가능"
            self._btn_analyze.setToolTip(tip)
            self._btn_utf8.setToolTip(tip)

    def run_apply_and_integrity_auto(self, parent: QWidget) -> bool:
        """Apply stub then auto integrity + UTF-8 — blocks until flow completes."""
        _ = parent
        if not self._vm:
            self._status_label.setText("적용 ✓ · 무결성 검사 (미구현)")
            logger.warning("integrity view model not configured")
            return True

        self._flow_ok = False
        self._progress_bar.setVisible(True)
        self._progress_bar.setRange(0, 0)
        self._status_label.setText("적용 완료 · 무결성 검사 중…")

        loop = QEventLoop(self)
        self._vm.finalize_flow_completed.connect(loop.quit)
        self._vm.finalize_flow_failed.connect(loop.quit)
        self._vm.start_auto_finalize_flow()
        loop.exec()

        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(100)
        if self._on_stats_refresh:
            self._on_stats_refresh()
        return self._flow_ok

    def _on_analyze_clicked(self) -> None:
        if not self._vm:
            return
        self._progress_bar.setVisible(True)
        self._progress_bar.setRange(0, 0)
        self._vm.start_integrity_only()

    def _on_utf8_clicked(self) -> None:
        if not self._vm:
            return
        self._progress_bar.setVisible(True)
        self._progress_bar.setRange(0, 0)
        self._vm.start_manual_utf8_convert(self)

    def _on_progress(self, progress) -> None:
        if progress.total:
            self._progress_bar.setRange(0, progress.total)
            self._progress_bar.setValue(progress.processed)
        else:
            self._progress_bar.setRange(0, 0)

    def _on_finalize_flow_completed(self, issue_count: int, converted: int) -> None:
        self._flow_ok = True
        utf8_part = f" · UTF-8 {converted:,}건" if converted else ""
        self._status_label.setText(f"적용 ✓ · 무결성 {issue_count:,}건{utf8_part}")

    def _on_finalize_flow_failed(self, message: str) -> None:
        self._flow_ok = False
        self._status_label.setText(f"검증 실패: {message}")

    def _on_integrity_only_completed(self, issue_count: int) -> None:
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(100)
        self._status_label.setText(f"무결성 검사 완료 · 이슈 {issue_count:,}건")
        if self._on_stats_refresh:
            self._on_stats_refresh()
