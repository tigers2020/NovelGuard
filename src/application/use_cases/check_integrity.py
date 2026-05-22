"""Check file integrity use case."""

from collections.abc import Callable
from pathlib import Path
from typing import Optional

from application.constants import Constants
from application.dto.integrity_check_request import IntegrityCheckRequest
from application.dto.integrity_check_result import IntegrityCheckResult
from application.dto.integrity_issue import IntegrityIssue as IntegrityIssueDto
from application.ports.file_content_reader import FileContentReader
from application.ports.file_data_store import IFileDataStore
from domain.ports.text_encoding import ITextEncodingDetector
from domain.services.integrity_check_service import IntegrityCheckService, normalize_encoding
from domain.value_objects.integrity_issue import IntegrityIssue as DomainIssue


class CheckIntegrityUseCase:
    """Run integrity rules over files in the data store."""

    def __init__(
        self,
        file_store: IFileDataStore,
        content_reader: FileContentReader,
        encoding_detector: ITextEncodingDetector,
    ) -> None:
        self._file_store = file_store
        self._content_reader = content_reader
        self._encoding_detector = encoding_detector

    def execute(
        self,
        request: IntegrityCheckRequest,
        *,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ) -> list[IntegrityCheckResult]:
        """Check integrity for requested files (or all files)."""
        files = self._resolve_files(request)
        total = len(files)
        results: list[IntegrityCheckResult] = []

        for index, file_data in enumerate(files):
            path = Path(file_data.path)
            message = path.name
            if progress_callback:
                progress_callback(index, total, message)

            sample = b""
            if path.is_file():
                try:
                    sample = self._content_reader.read_bytes(path, Constants.INTEGRITY_SAMPLE_BYTES)
                except OSError:
                    sample = b""

            detection = self._encoding_detector.detect(sample)
            encoding = normalize_encoding(detection.encoding)
            decode_ok = self._try_decode(sample, encoding or detection.encoding)

            domain_issues = IntegrityCheckService.evaluate(
                size=file_data.size,
                encoding=encoding or detection.encoding,
                confidence=detection.confidence,
                decode_ok=decode_ok,
                min_text_size=Constants.MIN_TEXT_FILE_SIZE,
                min_confidence=Constants.INTEGRITY_ENCODING_MIN_CONFIDENCE,
            )

            dto_issues = [_to_dto(issue) for issue in domain_issues]
            results.append(
                IntegrityCheckResult(
                    file_id=file_data.file_id,
                    issues=dto_issues,
                    encoding=encoding or detection.encoding,
                    encoding_confidence=detection.confidence,
                )
            )

        if progress_callback and total > 0:
            progress_callback(total, total, "완료")

        return results

    def _resolve_files(self, request: IntegrityCheckRequest):
        if request.file_ids is None:
            return self._file_store.get_all_files()
        out = []
        for file_id in request.file_ids:
            file_data = self._file_store.get_file(file_id)
            if file_data is not None:
                out.append(file_data)
        return out

    @staticmethod
    def _try_decode(sample: bytes, encoding: str | None) -> bool:
        if not sample:
            return True
        if not encoding:
            return False
        try:
            sample.decode(encoding, errors="strict")
            return True
        except (LookupError, UnicodeDecodeError):
            return False


def _to_dto(issue: DomainIssue) -> IntegrityIssueDto:
    return IntegrityIssueDto(
        rule_id=issue.rule_id.value,
        message=issue.message,
        severity=issue.severity,
    )
