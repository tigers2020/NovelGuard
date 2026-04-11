"""해시 서비스 어댑터 - IHashService 구현."""

import hashlib
from pathlib import Path

from domain.value_objects.detection_config import DetectionDefaults


class HashServiceAdapter:
    """IHashService 프로토콜 구현.

    파일 전체/prefix/suffix SHA256 해시를 계산합니다.
    Exact 중복 탐지에 사용됩니다.
    """

    def calculate_hash(self, file_path: Path) -> str:
        """전체 파일 해시 계산 (SHA256)."""
        h = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()

    def calculate_prefix_hash(
        self, file_path: Path, size: int = DetectionDefaults.SAMPLE_SIZE
    ) -> str:
        """파일 앞부분 해시 계산."""
        h = hashlib.sha256()
        with open(file_path, "rb") as f:
            data = f.read(size)
        h.update(data)
        return h.hexdigest()

    def calculate_suffix_hash(
        self, file_path: Path, size: int = DetectionDefaults.SAMPLE_SIZE
    ) -> str:
        """파일 뒷부분 해시 계산."""
        file_size = file_path.stat().st_size
        if file_size <= size:
            return self.calculate_hash(file_path)
        h = hashlib.sha256()
        with open(file_path, "rb") as f:
            f.seek(file_size - size)
            data = f.read(size)
        h.update(data)
        return h.hexdigest()
