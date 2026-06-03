"""Scan-time content probing with size-bucketed hashing and parallel I/O."""

from __future__ import annotations

import os
from collections import Counter
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

from domain.models import FileRecord, make_file_id
from infrastructure.file_content_probe import FileContentProbe, probe_file

ProgressCallback = Callable[[int, str], None]
CancelCheck = Callable[[], bool]
RecordSink = Callable[[FileRecord], None]

_DEFAULT_MAX_WORKERS = min(32, (os.cpu_count() or 4) + 4)
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


def _probe_entry(entry: _ScanPathEntry, *, hash_sizes: set[int]) -> FileContentProbe:
    need_hash = entry.size_bytes in hash_sizes
    return probe_file(
        entry.path,
        size_bytes=entry.size_bytes,
        need_hash=need_hash,
        need_near_text=False,
    )


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

    total = len(entries)
    completed = 0
    workers = max(1, min(max_workers, total))

    chunksize = max(1, min(64, total // (workers * 8) or 1))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for batch_start in range(0, total, _PROBE_BATCH_SIZE):
            if cancel_check():
                return
            batch = entries[batch_start : batch_start + _PROBE_BATCH_SIZE]
            probes = pool.map(
                lambda entry: _probe_entry(entry, hash_sizes=hash_sizes),
                batch,
                chunksize=chunksize,
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
