"""Streaming file content hashing."""

from __future__ import annotations

import hashlib
from pathlib import Path

from infrastructure.large_file_sampling import (
    SAMPLE_BYTES,
    content_fingerprint,
    is_large_file,
    read_head_tail,
)

_CHUNK_SIZE = 64 * 1024


def hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(_CHUNK_SIZE):
            digest.update(chunk)
    return digest.hexdigest()


def library_content_hash(path: Path, *, size_bytes: int | None = None) -> str:
    """Match scan-time `content_sha256` (full hash or large-file fingerprint)."""
    size = size_bytes if size_bytes is not None else path.stat().st_size
    if is_large_file(size):
        head, tail = read_head_tail(path, size, SAMPLE_BYTES)
        return content_fingerprint(size, head, tail)
    return hash_file(path)


def head_tail_apply_hash(path: Path, *, size_bytes: int | None = None) -> str:
    """Drift hash for head/tail variant groups (size excluded from sample)."""
    from domain.duplicate_content_variant import head_tail_sample_hash

    size = size_bytes if size_bytes is not None else path.stat().st_size
    sample = head_tail_sample_hash(path, size)
    if sample is None:
        return library_content_hash(path, size_bytes=size)
    return sample
