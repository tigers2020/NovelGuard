"""HashServiceAdapter staged fingerprint reads."""

from pathlib import Path

from domain.value_objects.detection_config import DetectionDefaults
from infrastructure.hashing.hash_service_adapter import HashServiceAdapter


def _sha256_hex(data: bytes) -> str:
    import hashlib

    return hashlib.sha256(data).hexdigest()


class TestReadStagedFingerprints:
    def test_small_file_prefix_covers_full_content(self, tmp_path: Path) -> None:
        data = b"small-novel-content"
        path = tmp_path / "small.txt"
        path.write_bytes(data)
        adapter = HashServiceAdapter()
        staged = adapter.read_staged_fingerprints(path, len(data), need_full=False)
        expected = _sha256_hex(data)
        assert staged.prefix_hash == expected
        assert staged.suffix_hash == expected
        assert staged.full_hash is None

    def test_small_file_need_full_returns_digest(self, tmp_path: Path) -> None:
        data = b"x" * 100
        path = tmp_path / "tiny.txt"
        path.write_bytes(data)
        adapter = HashServiceAdapter()
        staged = adapter.read_staged_fingerprints(path, len(data), need_full=True)
        expected = _sha256_hex(data)
        assert staged.full_hash == expected

    def test_large_file_prefix_suffix_and_optional_full(self, tmp_path: Path) -> None:
        sample = DetectionDefaults.SAMPLE_SIZE
        prefix_bytes = b"A" * sample
        middle = b"B" * 1000
        suffix_bytes = b"C" * sample
        data = prefix_bytes + middle + suffix_bytes
        path = tmp_path / "large.txt"
        path.write_bytes(data)
        adapter = HashServiceAdapter()
        staged = adapter.read_staged_fingerprints(path, len(data), need_full=False)
        assert staged.prefix_hash == _sha256_hex(prefix_bytes)
        assert staged.suffix_hash == _sha256_hex(suffix_bytes)
        assert staged.full_hash is None

        staged_full = adapter.read_staged_fingerprints(path, len(data), need_full=True)
        assert staged_full.full_hash == _sha256_hex(data)
