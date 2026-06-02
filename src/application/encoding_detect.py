"""Strict encoding detection for invalid_utf8 repair (PR-22)."""

from __future__ import annotations

from dataclasses import dataclass

from domain.repair_models import EncodingConfidence

_HIGH_ENCODINGS = ("cp949", "euc-kr", "shift_jis")
_LOW_ENCODING = "iso-8859-1"
_LOW_CONFIDENCE_WARNING = "iso-8859-1 fallback only; verify decoded text before applying repair."


@dataclass(frozen=True, slots=True)
class EncodingDetectionResult:
    encoding: str
    confidence: EncodingConfidence
    warning: str | None = None


def detect_source_encoding(data: bytes) -> EncodingDetectionResult | None:
    for encoding in _HIGH_ENCODINGS:
        try:
            data.decode(encoding, errors="strict")
        except UnicodeDecodeError:
            continue
        return EncodingDetectionResult(encoding=encoding, confidence="high")
    try:
        data.decode(_LOW_ENCODING, errors="strict")
    except UnicodeDecodeError:
        return None
    return EncodingDetectionResult(
        encoding=_LOW_ENCODING,
        confidence="low",
        warning=_LOW_CONFIDENCE_WARNING,
    )


def decode_bytes(data: bytes, encoding: str) -> str:
    return data.decode(encoding, errors="strict")
