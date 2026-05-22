"""Integrity check worker thread."""

from typing import Optional

from PySide6.QtCore import QObject, QThread, Signal

from application.dto.integrity_check_request import IntegrityCheckRequest
from application.dto.integrity_check_result import IntegrityCheckResult
from application.dto.job_types import JobProgress
from application.use_cases.check_integrity import CheckIntegrityUseCase
from gui.models.file_data_store import FileDataStore


class IntegrityWorker(QThread):
    """Run CheckIntegrityUseCase and apply results to FileDataStore."""

    integrity_completed = Signal(list)
    integrity_error = Signal(str)
    integrity_progress = Signal(object)

    def __init__(
        self,
        request: IntegrityCheckRequest,
        *,
        use_case: CheckIntegrityUseCase,
        file_data_store: FileDataStore,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self._request = request
        self._use_case = use_case
        self._store = file_data_store
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def run(self) -> None:
        try:

            def on_progress(processed: int, total: int, message: str) -> None:
                if self._cancelled:
                    return
                progress = JobProgress(
                    processed=processed,
                    total=total if total > 0 else None,
                    message=message,
                )
                self.integrity_progress.emit(progress)

            results = self._use_case.execute(self._request, progress_callback=on_progress)
            if self._cancelled:
                return
            self._apply_results(results)
            self.integrity_completed.emit(results)
        except Exception as exc:
            self.integrity_error.emit(str(exc))

    def _apply_results(self, results: list[IntegrityCheckResult]) -> None:
        for result in results:
            self._store.clear_integrity(result.file_id)
            if result.encoding:
                self._store.set_encoding(
                    result.file_id,
                    result.encoding,
                    result.encoding_confidence,
                )
            for issue in result.issues:
                self._store.add_integrity_issue(
                    result.file_id,
                    issue.message,
                    issue.severity,
                )
