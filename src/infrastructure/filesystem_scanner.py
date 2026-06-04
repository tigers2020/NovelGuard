from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from domain.duplicate_archive import LIBRARY_OUTPUT_DIR_NAMES
from domain.models import FileRecord, make_file_id
from infrastructure.scan_content_probe import (
    collect_scan_path_entries,
    enrich_scan_entries_with_content_probe,
)

PathsCollectedCallback = Callable[[int], None]
DEFAULT_EXTENSIONS = {".txt", ".md"}
ProgressCallback = Callable[[int, str], None]
CancelCheck = Callable[[], bool]
RecordSink = Callable[[FileRecord], None]
ContentHashFn = Callable[[Path], str]


@dataclass(frozen=True)
class ScanStreamResult:
    completed: bool
    cancelled: bool
    scanned_count: int = 0


def _relative_posix(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def scan_folder(
    folder_path: str,
    *,
    on_progress: ProgressCallback,
    cancel_check: CancelCheck,
    out: RecordSink,
    extensions: set[str] | None = None,
    include_hidden: bool = False,
    content_hash_fn: ContentHashFn | None = None,
    use_content_probe: bool = False,
) -> None:
    root = Path(folder_path).resolve()
    if not root.is_dir():
        raise ValueError(f"Not a directory: {folder_path}")

    allowed = extensions or DEFAULT_EXTENSIONS

    if use_content_probe:

        def on_collect_progress(pct: int, label: str) -> None:
            on_progress(min(pct, 2), label)

        def on_probe_progress(pct: int, label: str) -> None:
            # Reserve 2% for collect; map probe 0–100 → 2–100.
            mapped = 2 + int(pct * 98 / 100)
            on_progress(min(mapped, 100), label)

        entries = collect_scan_path_entries(
            root,
            allowed_extensions=allowed,
            include_hidden=include_hidden,
            cancel_check=cancel_check,
            on_progress=on_collect_progress,
        )
        if cancel_check():
            return
        enrich_scan_entries_with_content_probe(
            entries,
            on_progress=on_probe_progress,
            cancel_check=cancel_check,
            out=out,
        )
        return

    all_paths: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        if cancel_check():
            return
        if not include_hidden:
            dirnames[:] = [d for d in dirnames if not d.startswith(".")]
        dirnames[:] = [d for d in dirnames if d not in LIBRARY_OUTPUT_DIR_NAMES]
        for name in filenames:
            if not include_hidden and name.startswith("."):
                continue
            path = Path(dirpath) / name
            if path.suffix.lower() in allowed:
                all_paths.append(path)

    total = max(len(all_paths), 1)
    for i, path in enumerate(all_paths):
        if cancel_check():
            return
        st = path.stat()
        rel = _relative_posix(root, path)
        modified_at_ns = getattr(st, "st_mtime_ns", int(st.st_mtime * 1_000_000_000))
        content_sha256 = content_hash_fn(path) if content_hash_fn is not None else None
        record = FileRecord(
            id=make_file_id(rel, st.st_size, modified_at_ns),
            relative_path=rel,
            name=path.name,
            size_bytes=st.st_size,
            modified_at_ns=modified_at_ns,
            extension=path.suffix.lower(),
            content_sha256=content_sha256,
        )
        out(record)
        pct = int((i + 1) * 100 / total)
        on_progress(pct, f"파일 확인 중… ({i + 1}/{len(all_paths)})")


def scan_folder_stream(
    folder_path: str,
    *,
    on_progress: ProgressCallback,
    cancel_check: CancelCheck,
    on_record: RecordSink,
    extensions: set[str] | None = None,
    include_hidden: bool = False,
    on_paths_collected: PathsCollectedCallback | None = None,
) -> ScanStreamResult:
    """Walk + content-probe; emit FileRecord via on_record (no list[FileRecord] return)."""
    root = Path(folder_path).resolve()
    if not root.is_dir():
        raise ValueError(f"Not a directory: {folder_path}")

    allowed = extensions or DEFAULT_EXTENSIONS

    def on_collect_progress(pct: int, label: str) -> None:
        on_progress(min(pct, 2), label)

    def on_probe_progress(pct: int, label: str) -> None:
        mapped = 2 + int(pct * 98 / 100)
        on_progress(min(mapped, 100), label)

    entries = collect_scan_path_entries(
        root,
        allowed_extensions=allowed,
        include_hidden=include_hidden,
        cancel_check=cancel_check,
        on_progress=on_collect_progress,
    )
    total = len(entries)
    if on_paths_collected is not None:
        on_paths_collected(total)
    if cancel_check():
        return ScanStreamResult(completed=False, cancelled=True, scanned_count=0)
    enrich_scan_entries_with_content_probe(
        entries,
        on_progress=on_probe_progress,
        cancel_check=cancel_check,
        out=on_record,
    )
    if cancel_check():
        return ScanStreamResult(completed=False, cancelled=True, scanned_count=total)
    return ScanStreamResult(completed=True, cancelled=False, scanned_count=total)
