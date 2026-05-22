"""Content hash port (domain seam)."""

from pathlib import Path
from typing import Protocol

from domain.ports.staged_content_fingerprints import StagedContentFingerprints
from domain.value_objects.detection_config import DetectionDefaults


class IHashService(Protocol):
    """해시 서비스 인터페이스 — Exact 중복 탐지용."""

    def calculate_hash(self, file_path: Path) -> str:
        """전체 파일 해시 계산 (SHA256)."""
        ...

    def calculate_prefix_hash(
        self, file_path: Path, size: int = DetectionDefaults.SAMPLE_SIZE
    ) -> str:
        """파일 앞부분 해시 계산."""
        ...

    def calculate_suffix_hash(
        self, file_path: Path, size: int = DetectionDefaults.SAMPLE_SIZE
    ) -> str:
        """파일 뒷부분 해시 계산."""
        ...

    def read_staged_fingerprints(
        self,
        file_path: Path,
        file_size: int,
        *,
        need_full: bool = False,
    ) -> StagedContentFingerprints:
        """Single open: prefix + suffix samples; optional full SHA256 in same session."""
        ...
