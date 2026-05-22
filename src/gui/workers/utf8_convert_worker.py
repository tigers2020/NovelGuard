"""UTF-8 conversion worker thread."""

from typing import Optional

from PySide6.QtCore import QObject, QThread, Signal

from application.dto.job_types import JobProgress
from application.dto.utf8_convert_request import Utf8ConvertRequest
from application.use_cases.convert_files_to_utf8 import ConvertFilesToUtf8UseCase


class Utf8ConvertWorker(QThread):
    """Run ConvertFilesToUtf8UseCase on a background thread."""

    convert_completed = Signal(object)
    convert_error = Signal(str)
    convert_progress = Signal(object)

    def __init__(
        self,
        request: Utf8ConvertRequest,
        *,
        use_case: ConvertFilesToUtf8UseCase,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self._request = request
        self._use_case = use_case
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def run(self) -> None:
        try:
            if self._cancelled:
                return
            self.convert_progress.emit(
                JobProgress(processed=0, total=None, message="UTF-8 변환 준비…")
            )
            result = self._use_case.execute(self._request)
            if self._cancelled:
                return
            self.convert_completed.emit(result)
        except Exception as exc:
            self.convert_error.emit(str(exc))
