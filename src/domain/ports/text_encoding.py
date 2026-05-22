"""Text encoding detection port (domain seam)."""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class EncodingDetection:
    """Detected encoding from a byte sample."""

    encoding: str | None
    confidence: float


class ITextEncodingDetector(Protocol):
    """Detect text encoding from raw bytes (no I/O)."""

    def detect(self, sample: bytes) -> EncodingDetection: ...
