"""In-process session log buffer (PR-28)."""

from __future__ import annotations

import logging
import threading
from collections import deque
from datetime import UTC, datetime
from typing import Any

from application.log_query import (
    DEFAULT_LOG_LIMIT,
    clamp_log_limit,
    filter_entries_by_min_level,
    normalize_log_level,
)

_BUFFER: SessionLogBuffer | None = None
_HANDLER_ATTACHED = False

_NOVELGUARD_LOGGER_PREFIXES = ("app", "application", "domain", "infrastructure", "novelguard")


def accepts_novelguard_logger(name: str) -> bool:
    for prefix in _NOVELGUARD_LOGGER_PREFIXES:
        if name == prefix or name.startswith(f"{prefix}."):
            return True
    return False


class SessionLogBuffer:
    def __init__(self, maxlen: int = 2000) -> None:
        self._entries: deque[dict[str, Any]] = deque(maxlen=maxlen)
        self._lock = threading.Lock()

    def append(self, entry: dict[str, Any]) -> None:
        with self._lock:
            self._entries.append(entry)

    def query(self, *, level: str | None = None, limit: int = DEFAULT_LOG_LIMIT) -> list[dict[str, Any]]:
        with self._lock:
            snapshot = list(self._entries)
        filtered = filter_entries_by_min_level(snapshot, min_level=level)
        if len(filtered) <= limit:
            return filtered
        return filtered[-limit:]


class SessionLogHandler(logging.Handler):
    def __init__(self, buffer: SessionLogBuffer) -> None:
        super().__init__()
        self._buffer = buffer

    def emit(self, record: logging.LogRecord) -> None:
        if not accepts_novelguard_logger(record.name):
            return
        timestamp = datetime.fromtimestamp(record.created, tz=UTC).isoformat().replace("+00:00", "Z")
        level = record.levelname
        if level not in {"DEBUG", "INFO", "WARNING", "ERROR"}:
            level = "INFO"
        self._buffer.append(
            {
                "timestamp": timestamp,
                "level": level,
                "message": record.getMessage(),
                "logger": record.name,
            }
        )


def get_session_log_buffer() -> SessionLogBuffer:
    global _BUFFER
    if _BUFFER is None:
        _BUFFER = SessionLogBuffer()
    return _BUFFER


def attach_session_log_handler() -> None:
    global _HANDLER_ATTACHED
    if _HANDLER_ATTACHED:
        return
    buffer = get_session_log_buffer()
    handler = SessionLogHandler(buffer)
    handler.setLevel(logging.DEBUG)
    root = logging.getLogger()
    root.addHandler(handler)
    if root.level > logging.INFO:
        root.setLevel(logging.INFO)
    for prefix in _NOVELGUARD_LOGGER_PREFIXES:
        logging.getLogger(prefix).setLevel(logging.DEBUG)
    _HANDLER_ATTACHED = True


def query_log_entries(query: dict[str, Any]) -> dict[str, Any]:
    min_level = normalize_log_level(query.get("level"))
    limit = clamp_log_limit(query.get("limit", DEFAULT_LOG_LIMIT))
    entries = get_session_log_buffer().query(level=min_level, limit=limit)
    return {
        "entries": entries,
        "pageInfo": {"limit": limit, "hasMore": False},
    }
