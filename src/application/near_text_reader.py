"""Read text for near duplicate detection (PR-19)."""

from __future__ import annotations

from pathlib import Path

from domain.duplicate_near import extension_family
from domain.models import FileRecord
from infrastructure.large_file_sampling import near_text_from_head


def read_text_for_near_dup(
    root: Path,
    record: FileRecord,
    *,
    head_only: bool = True,
) -> str | None:
    if extension_family(record.extension) is None:
        return None
    if record.near_text_preview is not None:
        return record.near_text_preview
    path = root / record.relative_path
    if head_only:
        return near_text_from_head(path, record.size_bytes)
    try:
        data = path.read_bytes()
    except OSError:
        return None
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return None
