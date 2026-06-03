"""Orchestrate near duplicate detection (PR-19)."""

from __future__ import annotations

import os
from collections.abc import Mapping
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from application.near_text_reader import read_text_for_near_dup
from domain.duplicate_near import (
    NearDuplicateInput,
    NearDuplicateResult,
    find_near_duplicate_groups,
)
from domain.models import FileRecord

_NEAR_IO_PARALLEL_MIN_FILES = 256
_NEAR_IO_MAX_WORKERS = min(32, (os.cpu_count() or 4) + 4)


def build_exact_group_by_file_id(files: list[FileRecord]) -> dict[str, str]:
    from domain.duplicate_exact import find_exact_duplicate_groups

    mapping: dict[str, str] = {}
    for group in find_exact_duplicate_groups(files):
        for member_id in group.member_ids:
            mapping[member_id] = group.group_id
    return mapping


def _near_input_for_record(
    root: Path,
    record: FileRecord,
    *,
    head_only: bool,
) -> NearDuplicateInput:
    text = read_text_for_near_dup(root, record, head_only=head_only)
    return NearDuplicateInput(
        file_id=record.id,
        path=record.relative_path,
        extension=record.extension,
        content_hash=record.content_sha256,
        size_bytes=record.size_bytes,
        mtime_ns=record.modified_at_ns,
        text=text,
    )


def _build_near_inputs(
    root: Path,
    files: list[FileRecord],
    *,
    head_only: bool,
) -> list[NearDuplicateInput]:
    if len(files) < _NEAR_IO_PARALLEL_MIN_FILES:
        return [_near_input_for_record(root, record, head_only=head_only) for record in files]
    workers = max(1, min(_NEAR_IO_MAX_WORKERS, len(files)))
    chunksize = max(1, len(files) // (workers * 4))

    def build(record: FileRecord) -> NearDuplicateInput:
        return _near_input_for_record(root, record, head_only=head_only)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(build, files, chunksize=chunksize))


def run_near_duplicate_detection(
    *,
    root: Path,
    files: list[FileRecord],
    near_batch_id: str,
    exact_group_by_file_id: Mapping[str, str],
    large_library: bool = False,
) -> NearDuplicateResult:
    inputs = _build_near_inputs(root, files, head_only=True)
    return find_near_duplicate_groups(
        inputs,
        exact_group_by_file_id=exact_group_by_file_id,
        near_batch_id=near_batch_id,
        large_library=large_library,
    )
