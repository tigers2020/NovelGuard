"""해시 서비스 어댑터 - IHashService 구현."""

import hashlib
from pathlib import Path

from domain.ports.staged_content_fingerprints import StagedContentFingerprints
from domain.value_objects.detection_config import DetectionDefaults


class HashServiceAdapter:
    """IHashService 프로토콜 구현.

    파일 전체/prefix/suffix SHA256 해시를 계산합니다.
    Exact 중복 탐지에 사용됩니다.
    """

    def read_staged_fingerprints(
        self,
        file_path: Path,
        file_size: int,
        *,
        need_full: bool = False,
    ) -> StagedContentFingerprints:
        """Single open: prefix + suffix samples; optional full SHA256 in same session."""
        sample = DetectionDefaults.SAMPLE_SIZE
        with open(file_path, "rb") as f:
            prefix_data = f.read(min(file_size, sample))
            prefix_hash = hashlib.sha256(prefix_data).hexdigest()

            if file_size <= sample:
                suffix_hash = prefix_hash
                small_full: str | None = prefix_hash if need_full else None
                return StagedContentFingerprints(
                    prefix_hash=prefix_hash,
                    suffix_hash=suffix_hash,
                    full_hash=small_full,
                )

            f.seek(file_size - sample)
            suffix_data = f.read(sample)
            suffix_hash = hashlib.sha256(suffix_data).hexdigest()

            large_full: str | None = None
            if need_full:
                f.seek(0)
                h = hashlib.sha256()
                for chunk in iter(lambda: f.read(65536), b""):
                    h.update(chunk)
                large_full = h.hexdigest()

            return StagedContentFingerprints(
                prefix_hash=prefix_hash,
                suffix_hash=suffix_hash,
                full_hash=large_full,
            )

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
        file_size = file_path.stat().st_size
        return self.read_staged_fingerprints(file_path, file_size, need_full=False).prefix_hash

    def calculate_suffix_hash(
        self, file_path: Path, size: int = DetectionDefaults.SAMPLE_SIZE
    ) -> str:
        """파일 뒷부분 해시 계산."""
        file_size = file_path.stat().st_size
        return self.read_staged_fingerprints(file_path, file_size, need_full=False).suffix_hash
