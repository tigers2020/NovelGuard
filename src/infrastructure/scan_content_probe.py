"""Scan-time content probing with size-bucketed hashing and parallel I/O."""

from __future__ import annotations

import os
from collections import Counter
from collections.abc import Callable
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

from application.scan_pipeline_constants import (
    SCAN_STEM_HASH_MAX_GROUP_SIZE,
    SCAN_STEM_HASH_MIN_GROUP_SIZE,
)
from domain.filename_relation import normalize_filename_for_relation, title_stem_key
from domain.models import FileRecord, make_file_id
from infrastructure.file_content_probe import FileContentProbe, probe_file

ProgressCallback = Callable[[int, str], None]
CancelCheck = Callable[[], bool]
RecordSink = Callable[[FileRecord], None]

_DEFAULT_MAX_WORKERS = min(32, (os.cpu_count() or 4) + 4)
_PROBE_PROCESS_MIN_FILES = 256
_PROBE_PROCESS_MAX_WORKERS = min(8, (os.cpu_count() or 4))
_PROBE_BATCH_SIZE = 512
_PROGRESS_INTERVAL = 48


@dataclass(frozen=True, slots=True)
class _ScanPathEntry:
    path: Path
    relative_path: str
    name: str
    size_bytes: int
    modified_at_ns: int
    extension: str


def _entry_stem_hash_key(name: str, relative_path: str) -> str | None:
    parse = normalize_filename_for_relation(name, relative_path=relative_path)
    return title_stem_key(parse.normalized_stem)


def _entry_need_hash(
    entry: _ScanPathEntry,
    *,
    hash_sizes: set[int],
    hash_stem_keys: set[str],
) -> bool:
    stem_key = _entry_stem_hash_key(entry.name, entry.relative_path)
    return entry.size_bytes in hash_sizes or (stem_key is not None and stem_key in hash_stem_keys)


def _probe_entry(
    entry: _ScanPathEntry,
    *,
    hash_sizes: set[int],
    hash_stem_keys: set[str],
) -> FileContentProbe:
    return probe_file(
        entry.path,
        size_bytes=entry.size_bytes,
        need_hash=_entry_need_hash(entry, hash_sizes=hash_sizes, hash_stem_keys=hash_stem_keys),
        need_near_text=False,
    )


def _probe_entries_chunk(
    args: tuple[list[tuple[str, str, str, int]], frozenset[int], frozenset[str]],
) -> list[FileContentProbe]:
    """Process-pool worker: probe a chunk of files (reduces IPC vs one task per file)."""
    packed_entries, hash_sizes, hash_stem_keys = args
    results: list[FileContentProbe] = []
    for path_str, name, relative_path, size_bytes in packed_entries:
        stem_key = _entry_stem_hash_key(name, relative_path)
        need_hash = size_bytes in hash_sizes or (
            stem_key is not None and stem_key in hash_stem_keys
        )
        results.append(
            probe_file(
                Path(path_str),
                size_bytes=size_bytes,
                need_hash=need_hash,
                need_near_text=False,
            )
        )
    return results


def _probe_batch(
    batch: list[_ScanPathEntry],
    *,
    hash_sizes: set[int],
    hash_stem_keys: set[str],
    pool: ProcessPoolExecutor | ThreadPoolExecutor,
    worker_count: int,
    use_process_pool: bool,
) -> list[FileContentProbe]:
    frozen_sizes = frozenset(hash_sizes)
    frozen_stems = frozenset(hash_stem_keys)
    packed = [
        (str(entry.path), entry.name, entry.relative_path, entry.size_bytes) for entry in batch
    ]
    worker_chunk = max(32, min(256, len(packed) // max(1, worker_count) or 1))
    tasks = [
        (packed[i : i + worker_chunk], frozen_sizes, frozen_stems)
        for i in range(0, len(packed), worker_chunk)
    ]
    if use_process_pool:
        nested = pool.map(_probe_entries_chunk, tasks, chunksize=1)
    else:
        nested = pool.map(_probe_entries_chunk, tasks)
    return [probe for chunk in nested for probe in chunk]


def enrich_scan_entries_with_content_probe(
    entries: list[_ScanPathEntry],
    *,
    on_progress: ProgressCallback,
    cancel_check: CancelCheck,
    out: RecordSink,
    max_workers: int = _DEFAULT_MAX_WORKERS,
) -> None:
    if not entries:
        on_progress(100, "파일 확인 중… (0/0)")
        return

    size_counts = Counter(entry.size_bytes for entry in entries)
    hash_sizes = {size for size, count in size_counts.items() if count >= 2}

    stem_counts: Counter[str] = Counter()
    for entry in entries:
        stem_key = _entry_stem_hash_key(entry.name, entry.relative_path)
        if stem_key is not None:
            stem_counts[stem_key] += 1
    hash_stem_keys = {
        key
        for key, count in stem_counts.items()
        if SCAN_STEM_HASH_MIN_GROUP_SIZE <= count <= SCAN_STEM_HASH_MAX_GROUP_SIZE
    }

    total = len(entries)
    completed = 0
    use_process_pool = total >= _PROBE_PROCESS_MIN_FILES
    if use_process_pool:
        workers = max(1, min(_PROBE_PROCESS_MAX_WORKERS, total))
    else:
        workers = max(1, min(max_workers, total))

    executor_cls: type[ProcessPoolExecutor] | type[ThreadPoolExecutor]
    if use_process_pool:
        executor_cls = ProcessPoolExecutor
    else:
        executor_cls = ThreadPoolExecutor

    with executor_cls(max_workers=workers) as pool:
        for batch_start in range(0, total, _PROBE_BATCH_SIZE):
            if cancel_check():
                return
            batch = entries[batch_start : batch_start + _PROBE_BATCH_SIZE]
            probes = _probe_batch(
                batch,
                hash_sizes=hash_sizes,
                hash_stem_keys=hash_stem_keys,
                pool=pool,
                worker_count=workers,
                use_process_pool=use_process_pool,
            )
            for entry, probe in zip(batch, probes, strict=True):
                record = FileRecord(
                    id=make_file_id(entry.relative_path, entry.size_bytes, entry.modified_at_ns),
                    relative_path=entry.relative_path,
                    name=entry.name,
                    size_bytes=entry.size_bytes,
                    modified_at_ns=entry.modified_at_ns,
                    extension=entry.extension,
                    content_sha256=probe.content_sha256,
                    encoding_status=probe.encoding_status,
                    near_text_preview=None,
                )
                out(record)
                completed += 1
                if completed == total or completed % _PROGRESS_INTERVAL == 0:
                    pct = int(completed * 100 / total)
                    on_progress(pct, f"파일 확인 중… ({completed}/{total})")


def collect_scan_path_entries(
    root: Path,
    *,
    allowed_extensions: set[str],
    include_hidden: bool,
    cancel_check: CancelCheck,
    on_progress: ProgressCallback | None = None,
) -> list[_ScanPathEntry]:
    entries: list[_ScanPathEntry] = []
    discovered = 0
    for dirpath, dirnames, filenames in os.walk(root):
        if cancel_check():
            return entries
        if not include_hidden:
            dirnames[:] = [d for d in dirnames if not d.startswith(".")]
        for name in filenames:
            if not include_hidden and name.startswith("."):
                continue
            path = Path(dirpath) / name
            if path.suffix.lower() not in allowed_extensions:
                continue
            st = path.stat()
            rel = path.relative_to(root).as_posix()
            modified_at_ns = getattr(st, "st_mtime_ns", int(st.st_mtime * 1_000_000_000))
            entries.append(
                _ScanPathEntry(
                    path=path,
                    relative_path=rel,
                    name=path.name,
                    size_bytes=st.st_size,
                    modified_at_ns=modified_at_ns,
                    extension=path.suffix.lower(),
                )
            )
            discovered += 1
            if on_progress is not None and (discovered % 400 == 0 or discovered == 1):
                on_progress(0, f"파일 목록 수집 중 ({discovered})")
    if on_progress is not None and entries:
        on_progress(1, f"파일 목록 수집 완료 ({len(entries)})")
    return entries
