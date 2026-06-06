"""Detect hung cursor-agent runs, log diagnosis, and support worker retry."""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import TextIO

from automation.runners.cursor_runner import get_cursor_pid, is_cursor_proc_running

_DEFAULT_STALL_SECONDS = 900.0


@dataclass(frozen=True)
class StallDiagnosis:
    idle_seconds: float
    proc_running: bool
    cursor_pid: int | None
    log_path: str | None
    log_size_bytes: int | None
    log_mtime_age_seconds: float | None
    last_output_lines: tuple[str, ...]
    attempt: int
    likely_causes: tuple[str, ...]


class CursorOutputTracker:
    """Track last agent stdout/stderr line for stall detection."""

    def __init__(self, *, now: float | None = None) -> None:
        t = now if now is not None else time.time()
        self._last_line_at = t
        self._last_lines: deque[str] = deque(maxlen=20)

    def note_line(self, stream: str, line: str) -> None:
        self._last_line_at = time.time()
        self._last_lines.append(f"{stream}: {line}")

    def idle_seconds(self, *, now: float | None = None) -> float:
        t = now if now is not None else time.time()
        return max(0.0, t - self._last_line_at)

    @property
    def last_output_lines(self) -> tuple[str, ...]:
        return tuple(self._last_lines)


def _log_file_stats(log_path: str | None) -> tuple[int | None, float | None]:
    if not log_path:
        return None, None
    path = Path(log_path)
    if not path.is_file():
        return None, None
    stat = path.stat()
    return stat.st_size, max(0.0, time.time() - stat.st_mtime)


def diagnose_cursor_stall(
    *,
    tracker: CursorOutputTracker,
    attempt: int,
    log_path: str | None = None,
    now: float | None = None,
) -> StallDiagnosis:
    idle = tracker.idle_seconds(now=now)
    proc_running = is_cursor_proc_running()
    pid = get_cursor_pid()
    log_size, log_age = _log_file_stats(log_path)
    last_lines = tracker.last_output_lines

    causes: list[str] = []
    if proc_running and idle >= 30:
        causes.append(
            "cursor-agent process alive but no stdout/stderr "
            f"for {idle:.0f}s — likely MCP/tool wait, network, or CLI hang"
        )
    if not proc_running and idle >= 30:
        causes.append("cursor-agent not running while worker still expected output")
    if not last_lines:
        causes.append("no agent output yet — slow startup, auth, or stdin delivery stall")
    if log_path and log_size is not None and log_age is not None and log_age >= 30:
        causes.append(f"job log stale {log_age:.0f}s — agent may not be writing")
    if not causes:
        causes.append("idle threshold exceeded — investigate cursor-agent and job log")

    return StallDiagnosis(
        idle_seconds=idle,
        proc_running=proc_running,
        cursor_pid=pid,
        log_path=log_path,
        log_size_bytes=log_size,
        log_mtime_age_seconds=log_age,
        last_output_lines=last_lines,
        attempt=attempt,
        likely_causes=tuple(causes),
    )


def format_stall_diagnosis(diagnosis: StallDiagnosis) -> str:
    lines = [
        f"=== cursor stall diagnosis (attempt {diagnosis.attempt}) ===",
        f"idle_seconds: {diagnosis.idle_seconds:.1f}",
        f"proc_running: {diagnosis.proc_running}",
        f"cursor_pid: {diagnosis.cursor_pid}",
        f"log_path: {diagnosis.log_path}",
        f"log_size_bytes: {diagnosis.log_size_bytes}",
        f"log_mtime_age_seconds: {diagnosis.log_mtime_age_seconds}",
        "last_output:",
    ]
    if diagnosis.last_output_lines:
        lines.extend(f"  {row}" for row in diagnosis.last_output_lines)
    else:
        lines.append("  (none)")
    lines.append("likely_causes:")
    for cause in diagnosis.likely_causes:
        lines.append(f"  - {cause}")
    lines.append("=== end stall diagnosis ===")
    return "\n".join(lines) + "\n"


def write_stall_diagnosis(
    diagnosis: StallDiagnosis,
    *,
    log_file: TextIO | None = None,
    log_path: str | None = None,
) -> str:
    block = format_stall_diagnosis(diagnosis)
    if log_file is not None:
        log_file.write("\n" + block)
        log_file.flush()
    elif log_path:
        with Path(log_path).open("a", encoding="utf-8") as fh:
            fh.write("\n" + block)
    return block


def cursor_stall_config(cfg: dict) -> tuple[float, int, float]:
    """Return (stall_seconds, max_retries, poll_seconds)."""
    cursor_cfg = cfg.get("cursor") or {}
    stall_seconds = float(cursor_cfg.get("stall_seconds", _DEFAULT_STALL_SECONDS))
    max_retries = int(cursor_cfg.get("stall_max_retries", 1))
    poll_seconds = float(cursor_cfg.get("stall_poll_seconds", 5))
    return stall_seconds, max_retries, poll_seconds
