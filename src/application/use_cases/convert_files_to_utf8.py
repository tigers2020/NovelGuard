"""Convert text files to UTF-8 with backup."""

import shutil
from pathlib import Path

from application.constants import Constants
from application.dto.file_data import FileData
from application.dto.utf8_convert_request import Utf8ConvertMode, Utf8ConvertRequest
from application.dto.utf8_convert_result import Utf8ConvertResult
from application.exceptions import FileConvertError
from application.ports.file_content_reader import FileContentReader
from application.ports.file_data_store import IFileDataStore
from domain.services.integrity_check_service import normalize_encoding


class ConvertFilesToUtf8UseCase:
    """Convert eligible files to UTF-8 after integrity analysis."""

    def __init__(
        self,
        file_store: IFileDataStore,
        content_reader: FileContentReader,
    ) -> None:
        self._file_store = file_store
        self._content_reader = content_reader

    def execute(self, request: Utf8ConvertRequest) -> Utf8ConvertResult:
        """Convert files per mode; create .novelguard.bak before overwrite."""
        files = self._resolve_files(request)
        converted = 0
        skipped = 0
        failed = 0
        errors: list[str] = []

        for file_data in files:
            try:
                outcome = self._convert_one(file_data, request.mode)
            except (OSError, FileConvertError, UnicodeDecodeError) as exc:
                failed += 1
                errors.append(f"{file_data.path}: {exc}")
                continue

            if outcome == "converted":
                converted += 1
            else:
                skipped += 1

        return Utf8ConvertResult(
            converted=converted,
            skipped=skipped,
            failed=failed,
            errors=errors,
        )

    def _resolve_files(self, request: Utf8ConvertRequest) -> list[FileData]:
        if request.file_ids is None:
            candidates = self._file_store.get_all_files()
        else:
            candidates = []
            for file_id in request.file_ids:
                file_data = self._file_store.get_file(file_id)
                if file_data is not None:
                    candidates.append(file_data)
        return [f for f in candidates if self._is_eligible(f, request.mode)]

    def _is_eligible(self, file_data: FileData, mode: Utf8ConvertMode) -> bool:
        if file_data.size == 0:
            return False
        if any("디코드 실패" in msg or "0바이트" in msg for msg in file_data.integrity_issues):
            return False

        encoding = normalize_encoding(file_data.encoding)
        if encoding == "utf-8" or encoding is None:
            return False

        if mode == "auto_eligible":
            if file_data.integrity_severity == "ERROR":
                return False
            if file_data.encoding_confidence is None:
                return False
            if file_data.encoding_confidence < Constants.INTEGRITY_ENCODING_MIN_CONFIDENCE:
                return False
            return any("비 UTF-8" in msg for msg in file_data.integrity_issues)

        if mode == "manual_include_info":
            return True

        return file_data.integrity_severity in ("WARN", "ERROR")

    def _convert_one(self, file_data: FileData, mode: Utf8ConvertMode) -> str:
        path = Path(file_data.path)
        if not path.is_file():
            return "skipped"

        encoding = normalize_encoding(file_data.encoding)
        if not encoding or encoding == "utf-8":
            return "skipped"

        backup_path = Path(str(path) + Constants.UTF8_BACKUP_SUFFIX)
        if backup_path.exists():
            if backup_path.stat().st_mtime >= path.stat().st_mtime:
                return "skipped"

        raw = self._content_reader.read_bytes(path, max_bytes=None)
        try:
            text = raw.decode(encoding, errors="strict")
        except (LookupError, UnicodeDecodeError) as exc:
            if mode == "auto_eligible":
                return "skipped"
            raise FileConvertError(str(exc)) from exc

        if backup_path.exists():
            backup_path.unlink()
        shutil.copy2(path, backup_path)

        try:
            path.write_text(text, encoding="utf-8", newline="")
        except OSError as exc:
            shutil.copy2(backup_path, path)
            raise FileConvertError(str(exc)) from exc

        return "converted"
