from __future__ import annotations

import sys
import time

from automation.runners.display_mode import DisplayMode
from automation.runners.event_bus import Event, EventBus

_mode: DisplayMode = "plain"
_bus: EventBus | None = None


def init_emit(*, mode: DisplayMode, bus: EventBus) -> None:
    global _mode, _bus
    _mode = mode
    _bus = bus


def is_tui_mode() -> bool:
    return _mode == "tui"


def _plain_print(message: str) -> None:
    try:
        print(message, flush=True)
    except UnicodeEncodeError:
        encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
        sys.stdout.buffer.write((message + "\n").encode(encoding, errors="replace"))
        sys.stdout.buffer.flush()


def emit_or_print(
    source: str,
    kind: str,
    summary: str,
    *,
    detail: str | None = None,
    plain_prefix: str | None = None,
) -> None:
    if _mode == "plain":
        _plain_print(plain_prefix or f"[{source}] {summary}")
        return
    assert _bus is not None
    _bus.append(Event(ts=time.time(), source=source, kind=kind, summary=summary, detail=detail))
