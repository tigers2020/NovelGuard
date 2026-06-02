from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path

from domain.models import FileRecord, make_file_id

DEFAULT_EXTENSIONS = {".txt", ".md"}
ProgressCallback = Callable[[int, str], None]
CancelCheck = Callable[[], bool]
RecordSink = Callable[[FileRecord], None]
ContentHashFn = Callable[[Path], str]


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
) -> None:
    root = Path(folder_path).resolve()
    if not root.is_dir():
        raise ValueError(f"Not a directory: {folder_path}")

    allowed = extensions or DEFAULT_EXTENSIONS
    all_paths: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        if cancel_check():
            return
        if not include_hidden:
            dirnames[:] = [d for d in dirnames if not d.startswith(".")]
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
        on_progress(pct, f"스캔 중 ({i + 1}/{len(all_paths)})")
