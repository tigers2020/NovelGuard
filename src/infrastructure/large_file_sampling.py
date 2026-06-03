"""Bounded I/O for large files: head/tail samples instead of full reads."""

from __future__ import annotations

import codecs
import hashlib
from pathlib import Path

from domain.duplicate_near import MAX_NORMALIZED_CHARS

_CHUNK_SIZE = 64 * 1024
# Above this size, encoding and content fingerprint use head/tail samples only.
LARGE_FILE_THRESHOLD_BYTES = 2 * 1024 * 1024
SAMPLE_BYTES = 64 * 1024
NEAR_HEAD_BYTES = min(MAX_NORMALIZED_CHARS * 4, 256 * 1024)


def is_large_file(size_bytes: int) -> bool:
    return size_bytes > LARGE_FILE_THRESHOLD_BYTES


def read_head_bytes(path: Path, size: int, max_bytes: int) -> bytes:
    with path.open("rb") as handle:
        return handle.read(min(max_bytes, size))


def read_head_tail(path: Path, size: int, sample_bytes: int) -> tuple[bytes, bytes]:
    n = min(sample_bytes, size)
    if n == 0:
        return b"", b""
    with path.open("rb") as handle:
        head = handle.read(n)
        if size <= n:
            return head, b""
        if size <= 2 * n:
            tail = handle.read()
            return head, tail
        handle.seek(size - n)
        tail = handle.read(n)
    return head, tail


def utf8_valid_bytes(data: bytes) -> bool:
    if not data:
        return True
    try:
        data.decode("utf-8")
        return True
    except UnicodeDecodeError:
        return False


def utf8_valid_head_tail(head: bytes, tail: bytes) -> bool:
    return utf8_valid_bytes(head) and utf8_valid_bytes(tail)


def utf8_validate_path_sample(path: Path, size: int) -> str:
    if size == 0:
        return "empty"
    if is_large_file(size):
        head, tail = read_head_tail(path, size, SAMPLE_BYTES)
        return "utf-8" if utf8_valid_head_tail(head, tail) else "invalid_utf8"
    try:
        with path.open("rb") as handle:
            decoder = codecs.getincrementaldecoder("utf-8")()
            while chunk := handle.read(_CHUNK_SIZE):
                try:
                    decoder.decode(chunk)
                except UnicodeDecodeError:
                    return "invalid_utf8"
            decoder.decode(b"", final=True)
        return "utf-8"
    except OSError:
        return "read_error"


def content_fingerprint(size: int, head: bytes, tail: bytes) -> str:
    """Stable fingerprint for exact-dup bucketing (full hash for small files elsewhere)."""
    digest = hashlib.sha256()
    digest.update(size.to_bytes(8, "big"))
    digest.update(head)
    digest.update(tail)
    return digest.hexdigest()


def near_text_from_head(path: Path, size: int) -> str | None:
    data = read_head_bytes(path, size, NEAR_HEAD_BYTES)
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return None
