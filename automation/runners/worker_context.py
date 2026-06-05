"""Thread-local / daemon-scoped worker context (cancel, stop)."""

from __future__ import annotations

import threading

_stop_event: threading.Event | None = None


def set_stop_event(ev: threading.Event | None) -> None:
    global _stop_event
    _stop_event = ev


def stop_requested() -> bool:
    return _stop_event is not None and _stop_event.is_set()


def get_cancel_event() -> threading.Event | None:
    return _stop_event
