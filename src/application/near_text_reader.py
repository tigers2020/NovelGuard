"""Read text for near duplicate detection (PR-19)."""

from __future__ import annotations

from pathlib import Path

from domain.duplicate_near import extension_family
from domain.models import FileRecord
from infrastructure.large_file_sampling import NEAR_HEAD_BYTES, is_large_file, near_text_from_head

_MAX_READ_BYTES = NEAR_HEAD_BYTES


def read_text_for_near_dup(root: Path, record: FileRecord) -> str | None:
    if extension_family(record.extension) is None:
        return None
    if record.near_text_preview is not None:
        return record.near_text_preview
    path = root / record.relative_path
    if is_large_file(record.size_bytes):
        return near_text_from_head(path, record.size_bytes)
    try:
        data = path.read_bytes()
    except OSError:
        return None
    if len(data) > _MAX_READ_BYTES:
        data = data[:_MAX_READ_BYTES]
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return None
