from __future__ import annotations

import threading
from collections import deque
from dataclasses import dataclass


@dataclass(frozen=True)
class Event:
    ts: float
    source: str
    kind: str
    summary: str
    detail: str | None


class EventBus:
    def __init__(self, capacity: int = 500) -> None:
        self._events: deque[Event] = deque(maxlen=capacity)
        self._lock = threading.Lock()

    def append(self, event: Event) -> None:
        with self._lock:
            self._events.append(event)

    def tail(self, n: int, source: str | None = None) -> list[Event]:
        with self._lock:
            events = list(self._events)
        if source is not None:
            events = [e for e in events if e.source == source]
        return events[-n:]

    def cursor_lines(self, n: int = 40) -> list[str]:
        with self._lock:
            events = list(self._events)
        lines = [e.summary for e in events if e.kind == "cursor.line"]
        return lines[-n:]
