"""SimHash port (domain seam)."""

from pathlib import Path
from typing import Protocol

from domain.value_objects.detection_config import DetectionDefaults


class ISimHashService(Protocol):
    """SimHash 서비스 인터페이스 — Near 중복 탐지용."""

    def calculate_simhash(self, file_path: Path) -> int:
        """SimHash 계산 (전체 파일)."""
        ...

    def calculate_simhash_from_samples(
        self,
        file_path: Path,
        sample_size: int = DetectionDefaults.SAMPLE_SIZE,
    ) -> int:
        """SimHash 계산 (샘플링 기반)."""
        ...

    def calculate_similarity(self, simhash1: int, simhash2: int) -> float:
        """SimHash 유사도 계산 (0.0 ~ 1.0)."""
        ...
