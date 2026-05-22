"""Charset-normalizer encoding detector adapter."""

from charset_normalizer import from_bytes

from domain.ports.text_encoding import EncodingDetection


class CharsetNormalizerDetector:
    """Detect encoding using charset-normalizer."""

    def detect(self, sample: bytes) -> EncodingDetection:
        if not sample:
            return EncodingDetection(encoding=None, confidence=0.0)

        matches = from_bytes(sample)
        best = matches.best()
        if best is None:
            return EncodingDetection(encoding=None, confidence=0.0)

        chaos = float(best.chaos) if best.chaos is not None else 1.0
        coherence = float(best.coherence) if best.coherence is not None else 0.0
        confidence = max(0.0, min(1.0, 1.0 - chaos + coherence * 0.5))
        if confidence <= 0.0 and best.encoding:
            confidence = 0.8
        encoding = best.encoding
        return EncodingDetection(encoding=encoding, confidence=confidence)
