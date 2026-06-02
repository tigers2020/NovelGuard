"""Log entry query helpers (PR-28)."""

from __future__ import annotations

from typing import Any

LEVEL_RANK: dict[str, int] = {
    "DEBUG": 10,
    "INFO": 20,
    "WARNING": 30,
    "ERROR": 40,
}

DEFAULT_LOG_LIMIT = 200
MAX_LOG_LIMIT = 500


class LogQueryError(ValueError):
    def __init__(self, reason: str, message: str | None = None) -> None:
        self.reason = reason
        super().__init__(message or reason)


def clamp_log_limit(raw: object) -> int:
    try:
        value = int(raw)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        value = DEFAULT_LOG_LIMIT
    return min(max(1, value), MAX_LOG_LIMIT)


def normalize_log_level(raw: object) -> str | None:
    if raw is None:
        return None
    if not isinstance(raw, str):
        raise LogQueryError("INVALID_LOG_LEVEL")
    level = raw.strip().upper()
    if level not in LEVEL_RANK:
        raise LogQueryError("INVALID_LOG_LEVEL")
    return level


def filter_entries_by_min_level(
    entries: list[dict[str, Any]],
    *,
    min_level: str | None,
) -> list[dict[str, Any]]:
    if min_level is None:
        return entries
    threshold = LEVEL_RANK[min_level]
    filtered: list[dict[str, Any]] = []
    for entry in entries:
        level = str(entry.get("level", "INFO")).upper()
        if LEVEL_RANK.get(level, 0) >= threshold:
            filtered.append(entry)
    return filtered
