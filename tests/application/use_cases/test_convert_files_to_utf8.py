"""Tests for ConvertFilesToUtf8UseCase."""

import tempfile
from datetime import datetime
from pathlib import Path

from application.dto.file_data import FileData
from application.dto.utf8_convert_request import Utf8ConvertRequest
from application.use_cases.convert_files_to_utf8 import ConvertFilesToUtf8UseCase
from domain.entities.file_entry import FileEntry
from infrastructure.filesystem.file_content_reader import FileSystemContentReader


class Store:
    def __init__(self, files: list[FileData]) -> None:
        self.files = files

    def get_file(self, file_id: int):
        return next((f for f in self.files if f.file_id == file_id), None)

    def get_all_files(self):
        return self.files


def test_convert_cp949_to_utf8_with_backup() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "a.txt"
        path.write_bytes("안녕하세요".encode("cp949"))
        entry = FileEntry(
            path=path,
            size=path.stat().st_size,
            mtime=datetime(2025, 1, 1),
            extension=".txt",
            file_id=1,
        )
        file_data = FileData(
            entry=entry,
            file_id=1,
            encoding="cp949",
            encoding_confidence=0.95,
            integrity_issues=["비 UTF-8 (cp949)"],
            integrity_severity="INFO",
        )
        uc = ConvertFilesToUtf8UseCase(Store([file_data]), FileSystemContentReader())
        result = uc.execute(Utf8ConvertRequest(file_ids=[1], mode="auto_eligible"))
        assert result.converted == 1
        assert path.read_text(encoding="utf-8") == "안녕하세요"
        backup = Path(str(path) + ".novelguard.bak")
        assert backup.is_file()
