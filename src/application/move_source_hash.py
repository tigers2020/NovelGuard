"""Content hash/fingerprint for move preview and apply drift checks."""

from __future__ import annotations

from pathlib import Path

from infrastructure.content_hasher import hash_file
from infrastructure.large_file_sampling import (
    SAMPLE_BYTES,
    content_fingerprint,
    is_large_file,
    read_head_tail,
)


def content_hash_for_move(path: Path, *, size_bytes: int) -> str:
    """Match scan bucketing: fingerprint for large files, full SHA-256 otherwise."""
    if is_large_file(size_bytes):
        head, tail = read_head_tail(path, size_bytes, SAMPLE_BYTES)
        return content_fingerprint(size_bytes, head, tail)
    return hash_file(path)


