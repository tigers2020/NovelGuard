"""Integrity and UTF-8 conversion view model."""

from typing import Optional

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QCheckBox, QMessageBox, QWidget

from application.dto.integrity_check_request import IntegrityCheckRequest
from application.dto.job_types import JobEvent, JobType
from application.dto.utf8_convert_request import Utf8ConvertMode, Utf8ConvertRequest
from application.dto.utf8_convert_result import Utf8ConvertResult
from gui.models.file_data_store import FileDataStore
from gui.services.qt_job_manager import QtJobManager


def count_integrity_issues(store: FileDataStore) -> int:
    """Count files with WARN or ERROR integrity severity."""
    return sum(1 for f in store.get_all_files() if f.integrity_severity in ("WARN", "ERROR"))


class IntegrityViewModel(QObject):
    """Orchestrate integrity check and UTF-8 conversion jobs."""

    status_message = Signal(str)
    progress_changed = Signal(object)
    finalize_flow_completed = Signal(int, int)
    finalize_flow_failed = Signal(str)
    integrity_only_completed = Signal(int)

    def __init__(
        self,
        job_manager: QtJobManager,
        file_data_store: FileDataStore,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self._job_manager = job_manager
        self._store = file_data_store
        self._pending_integrity_job: int | None = None
        self._pending_utf8_job: int | None = None
        self._auto_chain_utf8 = False
        self._job_manager.subscribe(self._on_job_event)

    @property
    def has_files(self) -> bool:
        return self._store.get_file_count() > 0

    def start_auto_finalize_flow(self) -> None:
        """Integrity check then auto UTF-8 conversion."""
        self._auto_chain_utf8 = True
        self.status_message.emit("무결성 검사 중…")
        self._pending_integrity_job = self._job_manager.start_integrity_check(
            IntegrityCheckRequest()
        )

    def start_integrity_only(self) -> None:
        """Manual encoding analysis — no auto UTF-8."""
        self._auto_chain_utf8 = False
        self.status_message.emit("무결성 검사 중…")
        self._pending_integrity_job = self._job_manager.start_integrity_check(
            IntegrityCheckRequest()
        )

    def start_manual_utf8_convert(self, parent: QWidget) -> None:
        """User-confirmed UTF-8 conversion."""
        include_info = False
        msg = QMessageBox(parent)
        msg.setWindowTitle("UTF-8 변환")
        msg.setText("선택한 범위의 파일을 UTF-8로 변환합니다. 백업(.novelguard.bak)을 생성합니다.")
        checkbox = QCheckBox("비 UTF-8(INFO) 포함")
        msg.setCheckBox(checkbox)
        msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if msg.exec() != QMessageBox.StandardButton.Yes:
            return
        include_info = checkbox.isChecked()
        mode: Utf8ConvertMode = "manual_include_info" if include_info else "manual_default"
        self._auto_chain_utf8 = False
        self.status_message.emit("UTF-8 변환 중… (백업 생성)")
        self._pending_utf8_job = self._job_manager.start_utf8_convert(
            Utf8ConvertRequest(file_ids=None, mode=mode)
        )

    def _on_job_event(self, event: JobEvent) -> None:
        if event.event_type == "progress" and "progress" in event.data:
            if event.job_type in (JobType.INTEGRITY, JobType.ENCODING):
                self.progress_changed.emit(event.data["progress"])
            return

        if event.job_type == JobType.INTEGRITY:
            if event.event_type == "completed" and event.job_id == self._pending_integrity_job:
                self._pending_integrity_job = None
                issue_count = count_integrity_issues(self._store)
                if self._auto_chain_utf8:
                    self.status_message.emit("UTF-8 변환 중… (백업 생성)")
                    self._pending_utf8_job = self._job_manager.start_utf8_convert(
                        Utf8ConvertRequest(file_ids=None, mode="auto_eligible")
                    )
                else:
                    self.status_message.emit(f"무결성 검사 완료 · 이슈 {issue_count:,}건")
                    self.integrity_only_completed.emit(issue_count)
            elif event.event_type == "failed" and event.job_id == self._pending_integrity_job:
                self._pending_integrity_job = None
                error = str(event.data.get("error", "무결성 검사 실패"))
                self.finalize_flow_failed.emit(error)
            return

        if event.job_type == JobType.ENCODING:
            if event.event_type == "completed" and event.job_id == self._pending_utf8_job:
                self._pending_utf8_job = None
                result = event.data.get("result")
                converted = result.converted if isinstance(result, Utf8ConvertResult) else 0
                issue_count = count_integrity_issues(self._store)
                if self._auto_chain_utf8:
                    self._auto_chain_utf8 = False
                    self.finalize_flow_completed.emit(issue_count, converted)
                else:
                    self.status_message.emit(
                        f"UTF-8 변환 완료 · {converted:,}건 변환 · 이슈 {issue_count:,}건"
                    )
            elif event.event_type == "failed" and event.job_id == self._pending_utf8_job:
                self._pending_utf8_job = None
                error = str(event.data.get("error", "UTF-8 변환 실패"))
                if self._auto_chain_utf8:
                    self._auto_chain_utf8 = False
                    self.finalize_flow_failed.emit(error)
                else:
                    self.status_message.emit(error)
