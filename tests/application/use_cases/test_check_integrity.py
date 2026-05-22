"""Tests for CheckIntegrityUseCase."""

from datetime import datetime
from pathlib import Path

from application.dto.file_data import FileData
from application.dto.integrity_check_request import IntegrityCheckRequest
from application.use_cases.check_integrity import CheckIntegrityUseCase
from domain.entities.file_entry import FileEntry
from domain.ports.text_encoding import EncodingDetection


class FakeReader:
    def read_bytes(self, path: Path, max_bytes: int | None = None) -> bytes:
        return b"hello"


class FakeDetector:
    def detect(self, sample: bytes) -> EncodingDetection:
        return EncodingDetection(encoding="utf-8", confidence=0.99)


class FakeStore:
    def __init__(self) -> None:
        entry = FileEntry(
            path=Path("/tmp/a.txt"),
            size=500,
            mtime=datetime(2025, 1, 1),
            extension=".txt",
            file_id=1,
        )
        self.files = [FileData(entry=entry, file_id=1)]

    def get_file(self, file_id: int):
        return next((f for f in self.files if f.file_id == file_id), None)

    def get_all_files(self):
        return self.files


def test_check_integrity_returns_result() -> None:
    uc = CheckIntegrityUseCase(FakeStore(), FakeReader(), FakeDetector())
    results = uc.execute(IntegrityCheckRequest())
    assert len(results) == 1
    assert results[0].file_id == 1
    assert results[0].encoding == "utf-8"
