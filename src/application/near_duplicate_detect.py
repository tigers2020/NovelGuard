"""Orchestrate near duplicate detection (PR-19)."""

from __future__ import annotations

import os
from collections.abc import Mapping
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from pathlib import Path

from application.near_text_reader import read_text_for_near_dup
from domain.duplicate_near import (
    NEAR_DUP_THRESHOLD,
    NearDuplicateInput,
    NearDuplicateResult,
    find_near_duplicate_groups,
    find_near_duplicate_groups_from_prepared,
    prepare_near_duplicate_input,
)
from domain.models import FileRecord

_NEAR_IO_PARALLEL_MIN_FILES = 256
_NEAR_PROCESS_PREPARE_MIN_FILES = 512
_NEAR_IO_MAX_WORKERS = min(32, (os.cpu_count() or 4) + 4)
_NEAR_PROCESS_MAX_WORKERS = min(8, (os.cpu_count() or 4))


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


def _load_and_prepare_near_file(args: tuple[str, FileRecord]):
    """Process-pool worker: read head text and build prepared near-dup entry."""
    root_str, record = args
    text = read_text_for_near_dup(Path(root_str), record, head_only=True)
    item = NearDuplicateInput(
        file_id=record.id,
        path=record.relative_path,
        extension=record.extension,
        content_hash=record.content_sha256,
        size_bytes=record.size_bytes,
        mtime_ns=record.modified_at_ns,
        text=text,
    )
    return prepare_near_duplicate_input(item)


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


def _run_near_detection_multiprocess(
    *,
    root: Path,
    files: list[FileRecord],
    near_batch_id: str,
    exact_group_by_file_id: Mapping[str, str],
    large_library: bool,
) -> NearDuplicateResult:
    root_str = str(root)
    workers = max(1, min(_NEAR_PROCESS_MAX_WORKERS, len(files)))
    chunksize = max(16, len(files) // (workers * 8))
    prepared = []
    skipped = 0
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for ready in pool.map(
            _load_and_prepare_near_file,
            ((root_str, record) for record in files),
            chunksize=chunksize,
        ):
            if ready is None:
                skipped += 1
            else:
                prepared.append(ready)
    return find_near_duplicate_groups_from_prepared(
        prepared,
        skipped=skipped,
        exact_group_by_file_id=exact_group_by_file_id,
        near_batch_id=near_batch_id,
        threshold=NEAR_DUP_THRESHOLD,
        large_library=large_library,
    )


def run_near_duplicate_detection(
    *,
    root: Path,
    files: list[FileRecord],
    near_batch_id: str,
    exact_group_by_file_id: Mapping[str, str],
    large_library: bool = False,
) -> NearDuplicateResult:
    if len(files) >= _NEAR_PROCESS_PREPARE_MIN_FILES:
        return _run_near_detection_multiprocess(
            root=root,
            files=files,
            near_batch_id=near_batch_id,
            exact_group_by_file_id=exact_group_by_file_id,
            large_library=large_library,
        )
    inputs = _build_near_inputs(root, files, head_only=True)
    return find_near_duplicate_groups(
        inputs,
        exact_group_by_file_id=exact_group_by_file_id,
        near_batch_id=near_batch_id,
        large_library=large_library,
    )
