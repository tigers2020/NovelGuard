"""Tests for CharsetNormalizerDetector."""

from infrastructure.encoding.charset_normalizer_detector import CharsetNormalizerDetector


def test_detect_utf8() -> None:
    det = CharsetNormalizerDetector()
    result = det.detect("hello".encode())
    assert result.encoding is not None
    assert result.confidence > 0
