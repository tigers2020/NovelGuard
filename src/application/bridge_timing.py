"""Structured timing spans for bridge, lock, SQLite, and post-scan phases (NOV-39)."""

from __future__ import annotations

import json
import logging
import threading
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from functools import wraps
from typing import Any, TypeVar

_LOGGER = logging.getLogger("application.bridge_timing")

F = TypeVar("F", bound=Callable[..., Any])

_LOCK_TIMING_MIN_MS = 1


def _error_code_from_exc(exc: BaseException) -> str:
    reason = getattr(exc, "reason", None)
    if isinstance(reason, str) and reason:
        return reason
    return type(exc).__name__


def log_timing_event(**fields: Any) -> None:
    payload = {
        key: value for key, value in fields.items() if value is not None or key == "error_code"
    }
    _LOGGER.debug("%s", json.dumps(payload, ensure_ascii=False))


@dataclass
class BridgeTimingSpan:
    method: str
    t0: float = field(default_factory=time.perf_counter)


@contextmanager
def bridge_method_span(method: str) -> Iterator[BridgeTimingSpan]:
    span = BridgeTimingSpan(method=method)
    ok = True
    error_code: str | None = None
    try:
        yield span
    except BaseException as exc:
        ok = False
        error_code = _error_code_from_exc(exc)
        raise
    finally:
        elapsed_ms = int((time.perf_counter() - span.t0) * 1000)
        log_timing_event(
            event="bridge_timing",
            method=method,
            elapsed_ms=elapsed_ms,
            ok=ok,
            error_code=error_code,
        )


def bridge_timing_decorator(method: str | None = None) -> Callable[[F], F]:
    def decorator(fn: F) -> F:
        span_name = method or fn.__name__

        @wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            with bridge_method_span(span_name):
                return fn(*args, **kwargs)

        return wrapper  # type: ignore[return-value]

    return decorator


@contextmanager
def lock_wait_scope(
    lock: threading.RLock,
    *,
    caller: str,
    holder_pipeline_phase: str,
    holder_background_phase: str,
) -> Iterator[None]:
    t0 = time.perf_counter()
    lock.acquire()
    lock_wait_ms = int((time.perf_counter() - t0) * 1000)
    if lock_wait_ms >= _LOCK_TIMING_MIN_MS:
        log_timing_event(
            event="lock_timing",
            caller=caller,
            lock_wait_ms=lock_wait_ms,
            holder_pipeline_phase=holder_pipeline_phase,
            holder_background_phase=holder_background_phase,
        )
    try:
        yield
    finally:
        lock.release()


@dataclass
class SqliteTimingSpan:
    query_type: str
    t0: float = field(default_factory=time.perf_counter)
    row_count: int = 0
    limit: int | None = None
    offset: int | None = None


@contextmanager
def sqlite_query_span(query_type: str) -> Iterator[SqliteTimingSpan]:
    span = SqliteTimingSpan(query_type=query_type)
    try:
        yield span
    finally:
        query_ms = int((time.perf_counter() - span.t0) * 1000)
        fields: dict[str, Any] = {
            "event": "sqlite_timing",
            "query_type": query_type,
            "query_ms": query_ms,
            "row_count": span.row_count,
        }
        if span.limit is not None:
            fields["limit"] = span.limit
        if span.offset is not None:
            fields["offset"] = span.offset
        log_timing_event(**fields)


def log_phase_start(phase: str) -> float:
    return time.perf_counter()


def log_phase_end(phase: str, t0: float, *, status: str = "complete") -> None:
    finished_at = datetime.now(tz=UTC).isoformat().replace("+00:00", "Z")
    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    log_timing_event(
        event="phase_timing",
        phase=phase,
        finished_at=finished_at,
        elapsed_ms=elapsed_ms,
        status=status,
    )


def instrument_bridge_api(cls: type) -> type:
    """Wrap every public method on a bridge API class (except dunder)."""
    for name, attr in list(vars(cls).items()):
        if name.startswith("_") or not callable(attr):
            continue
        setattr(cls, name, bridge_timing_decorator(name)(attr))
    return cls
