"""Read trailing lines from automation job logs (TUI agent panel fallback)."""

from __future__ import annotations

import time
from pathlib import Path


def read_log_tail(
    path: str | None,
    *,
    max_lines: int = 40,
    max_bytes: int = 256_000,
) -> tuple[list[str], float | None]:
    """Return last ``max_lines`` and seconds since log mtime (None if missing)."""
    if not path:
        return [], None
    log_path = Path(path)
    if not log_path.is_file():
        return [], None
    try:
        mtime_age = max(0.0, time.time() - log_path.stat().st_mtime)
        raw = log_path.read_bytes()
    except OSError:
        return [], None
    if len(raw) > max_bytes:
        raw = raw[-max_bytes:]
    text = raw.decode("utf-8", errors="replace")
    lines = [ln.rstrip("\r") for ln in text.splitlines()]
    if len(lines) > max_lines:
        lines = lines[-max_lines:]
    return lines, mtime_age
