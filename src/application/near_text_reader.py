"""Read text for near duplicate detection (PR-19)."""

from __future__ import annotations

from pathlib import Path

from domain.duplicate_near import MAX_NORMALIZED_CHARS, extension_family
from domain.models import FileRecord

_MAX_READ_BYTES = MAX_NORMALIZED_CHARS * 4


def read_text_for_near_dup(root: Path, record: FileRecord) -> str | None:
    if extension_family(record.extension) is None:
        return None
    path = root / record.relative_path
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
