"""해시 서비스 포트 인터페이스."""

from pathlib import Path
from typing import Protocol

from domain.value_objects.detection_config import DetectionDefaults


class IHashService(Protocol):
    """해시 서비스 인터페이스.

    Infrastructure 계층에서 구현하여 Exact 중복 탐지에 사용.
    """

    def calculate_hash(self, file_path: Path) -> str:
        """전체 파일 해시 계산 (SHA256).

        Args:
            file_path: 파일 경로.

        Returns:
            해시 값 (hex 문자열).
        """
        ...

    def calculate_prefix_hash(
        self, file_path: Path, size: int = DetectionDefaults.SAMPLE_SIZE
    ) -> str:
        """파일 앞부분 해시 계산.

        Args:
            file_path: 파일 경로.
            size: 읽을 바이트 수 (기본값: 64KB).

        Returns:
            해시 값 (hex 문자열).
        """
        ...

    def calculate_suffix_hash(
        self, file_path: Path, size: int = DetectionDefaults.SAMPLE_SIZE
    ) -> str:
        """파일 뒷부분 해시 계산.

        Args:
            file_path: 파일 경로.
            size: 읽을 바이트 수 (기본값: 64KB).

        Returns:
            해시 값 (hex 문자열).
        """
        ...


class ISimHashService(Protocol):
    """SimHash 서비스 인터페이스.

    Infrastructure 계층에서 구현하여 Near 중복 탐지에 사용 (v2 기능).
    """

    def calculate_simhash(self, file_path: Path) -> int:
        """SimHash 계산 (전체 파일).

        Args:
            file_path: 파일 경로.

        Returns:
            SimHash 값 (64비트 정수).
        """
        ...

    def calculate_simhash_from_samples(
        self,
        file_path: Path,
        sample_size: int = DetectionDefaults.SAMPLE_SIZE,
    ) -> int:
        """SimHash 계산 (샘플링 기반).

        Args:
            file_path: 파일 경로.
            sample_size: 샘플 크기 (바이트, 기본값: 64KB).

        Returns:
            SimHash 값 (64비트 정수).
        """
        ...

    def calculate_similarity(self, simhash1: int, simhash2: int) -> float:
        """SimHash 유사도 계산.

        Args:
            simhash1: 첫 번째 SimHash.
            simhash2: 두 번째 SimHash.

        Returns:
            유사도 (0.0 ~ 1.0).
        """
        ...
