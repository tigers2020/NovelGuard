"""Scan-time file probe: sampled I/O for large files, single read for small."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from infrastructure.large_file_sampling import (
    NEAR_HEAD_BYTES,
    SAMPLE_BYTES,
    content_fingerprint,
    is_large_file,
    near_text_from_head,
    read_head_tail,
    utf8_valid_bytes,
    utf8_valid_head_tail,
)


@dataclass(frozen=True, slots=True)
class FileContentProbe:
    content_sha256: str | None
    encoding_status: str | None
    near_text_preview: str | None


def probe_file(
    path: Path,
    *,
    size_bytes: int,
    need_hash: bool,
    need_near_text: bool,
) -> FileContentProbe:
    if size_bytes == 0:
        return FileContentProbe(None, "empty", None)

    if is_large_file(size_bytes):
        return _probe_large(path, size_bytes, need_hash=need_hash, need_near_text=need_near_text)

    if not need_hash:
        # Head/tail sample: for tiny files this reads the whole file; for larger files
        # skips full read when only encoding (and optional near preview) is needed.
        return _probe_sample_encoding(
            path,
            size_bytes,
            need_near_text=need_near_text,
        )

    return _probe_small(path, need_hash=need_hash, need_near_text=need_near_text)


def _probe_large(
    path: Path,
    size: int,
    *,
    need_hash: bool,
    need_near_text: bool,
) -> FileContentProbe:
    try:
        head, tail = read_head_tail(path, size, SAMPLE_BYTES)
    except OSError:
        return FileContentProbe(None, "read_error", None)

    encoding_status = "utf-8" if utf8_valid_head_tail(head, tail) else "invalid_utf8"
    content_sha256 = content_fingerprint(size, head, tail) if need_hash else None
    near_text: str | None = None
    if need_near_text and encoding_status == "utf-8":
        if len(head) >= min(size, NEAR_HEAD_BYTES):
            try:
                near_text = head[:NEAR_HEAD_BYTES].decode("utf-8")
            except UnicodeDecodeError:
                near_text = None
        else:
            near_text = near_text_from_head(path, size)

    return FileContentProbe(content_sha256, encoding_status, near_text)


def _probe_sample_encoding(
    path: Path,
    size: int,
    *,
    need_near_text: bool,
) -> FileContentProbe:
    try:
        head, tail = read_head_tail(path, size, SAMPLE_BYTES)
    except OSError:
        return FileContentProbe(None, "read_error", None)

    encoding_status = "utf-8" if utf8_valid_head_tail(head, tail) else "invalid_utf8"
    near_text: str | None = None
    if need_near_text and encoding_status == "utf-8":
        try:
            near_text = head[:NEAR_HEAD_BYTES].decode("utf-8")
        except UnicodeDecodeError:
            near_text = None
    return FileContentProbe(None, encoding_status, near_text)


def _probe_small(
    path: Path,
    *,
    need_hash: bool,
    need_near_text: bool,
) -> FileContentProbe:
    try:
        data = path.read_bytes()
    except OSError:
        return FileContentProbe(None, "read_error", None)

    encoding_status = "utf-8" if utf8_valid_bytes(data) else "invalid_utf8"
    content_sha256 = hashlib.sha256(data).hexdigest() if need_hash else None
    near_text: str | None = None
    if need_near_text and encoding_status == "utf-8":
        try:
            near_text = data[:NEAR_HEAD_BYTES].decode("utf-8")
        except UnicodeDecodeError:
            near_text = None

    return FileContentProbe(content_sha256, encoding_status, near_text)
