"""Work screen summary strip ViewModel."""

from typing import Optional

from PySide6.QtCore import QObject, Signal

from application.dto.job_types import JobEvent, JobType
from application.ports.job_runner import IJobRunner
from application.ports.log_sink import ILogSink
from gui.models.app_state import AppState
from gui.services.work_stats import compute_work_stats
from gui.view_models.work_dto import DuplicateState, LibraryState, WorkSummary


class WorkViewModel(QObject):
    """Aggregates AppState + store + job flags for summary strip."""

    summary_changed = Signal(object)  # WorkSummary

    def __init__(
        self,
        app_state: AppState,
        job_manager: Optional[IJobRunner] = None,
        log_sink: Optional[ILogSink] = None,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self._app_state = app_state
        self._job_manager = job_manager
        self._log_sink = log_sink
        self._preview_running = False
        self._active_jobs: set[JobType] = set()

        if job_manager:
            job_manager.subscribe(self._on_job_event)

    def set_preview_running(self, running: bool) -> None:
        self._preview_running = running
        self.refresh()

    def refresh(self) -> None:
        self.summary_changed.emit(self.build_summary())

    def build_summary(self) -> WorkSummary:
        stats = compute_work_stats(self._app_state.file_data_store)
        folder = self._app_state.scan_folder

        library_state: LibraryState = "idle"
        if not folder:
            library_state = "idle"
        elif self._preview_running:
            library_state = "previewing"
        elif self._is_job_running(JobType.SCAN):
            library_state = "scanning"
        elif stats.total_files > 0:
            library_state = "ready"

        duplicate_state: DuplicateState
        if self._is_job_running(JobType.DUPLICATE):
            duplicate_state = "running"
        elif stats.duplicate_groups > 0:
            duplicate_state = "ready"
        elif stats.total_files > 0:
            duplicate_state = "empty"
        else:
            duplicate_state = "idle"

        return WorkSummary(
            folder_path=folder,
            total_files=stats.total_files,
            duplicate_groups=stats.duplicate_groups,
            saved_gb=stats.saved_gb,
            integrity_issues=stats.integrity_issues,
            library_state=library_state,
            duplicate_state=duplicate_state,
        )

    def _is_job_running(self, job_type: JobType) -> bool:
        return job_type in self._active_jobs

    def _on_job_event(self, event: JobEvent) -> None:
        if event.event_type == "started":
            self._active_jobs.add(event.job_type)
        elif event.event_type in ("completed", "failed", "cancelled"):
            self._active_jobs.discard(event.job_type)
        self.refresh()
