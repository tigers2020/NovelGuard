from __future__ import annotations

import json
import logging
import threading
import time
from pathlib import Path

import pytest

from app.bridge_api import BridgeApi
from app.bridge_contract import PreviewApplyError
from app.bridge_parity import PYWEBVIEW_API_METHODS
from app.session_factory import create_bridge_api, create_library_session
from application.bridge_timing import (
    bridge_method_span,
    bridge_timing_decorator,
    lock_wait_scope,
    log_phase_end,
    log_phase_start,
    log_timing_event,
    sqlite_query_span,
)
from infrastructure.sqlite_library_index import SqliteLibraryIndex


def _parse_debug_records(caplog: pytest.LogCaptureFixture) -> list[dict]:
    out: list[dict] = []
    for record in caplog.records:
        if record.levelno != logging.DEBUG:
            continue
        try:
            out.append(json.loads(record.getMessage()))
        except json.JSONDecodeError:
            continue
    return out


def _timing_events(caplog: pytest.LogCaptureFixture, event: str) -> list[dict]:
    caplog.set_level(logging.DEBUG)
    return [p for p in _parse_debug_records(caplog) if p.get("event") == event]


def test_log_timing_event_emits_json(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG, logger="application.bridge_timing")
    log_timing_event(
        event="bridge_timing", method="get_snapshot", elapsed_ms=12, ok=True, error_code=None
    )
    payloads = _parse_debug_records(caplog)
    assert payloads == [
        {
            "event": "bridge_timing",
            "method": "get_snapshot",
            "elapsed_ms": 12,
            "ok": True,
            "error_code": None,
        }
    ]


def test_bridge_method_span_success(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG, logger="application.bridge_timing")
    with bridge_method_span("query_review_rows"):
        pass
    payloads = _timing_events(caplog, "bridge_timing")
    assert len(payloads) == 1
    assert payloads[0]["event"] == "bridge_timing"
    assert payloads[0]["method"] == "query_review_rows"
    assert payloads[0]["ok"] is True
    assert payloads[0]["error_code"] is None
    assert isinstance(payloads[0]["elapsed_ms"], int)


def test_bridge_method_span_maps_preview_apply_error(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG, logger="application.bridge_timing")
    with pytest.raises(PreviewApplyError):
        with bridge_method_span("set_work_mode"):
            raise PreviewApplyError("INVALID_WORK_MODE", "bad mode")
    payloads = _timing_events(caplog, "bridge_timing")
    assert payloads[0]["ok"] is False
    assert payloads[0]["error_code"] == "INVALID_WORK_MODE"


def test_lock_wait_scope_emits_when_contended(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG, logger="application.bridge_timing")
    lock = threading.Lock()
    lock.acquire()
    try:

        def release_after_delay() -> None:
            time.sleep(0.02)
            lock.release()

        t = threading.Thread(target=release_after_delay)
        t.start()
        with lock_wait_scope(
            lock,  # type: ignore[arg-type]
            caller="query_review_rows",
            holder_pipeline_phase="analyze",
            holder_background_phase="near",
        ):
            pass
        t.join()
    finally:
        if lock.locked():
            try:
                lock.release()
            except RuntimeError:
                pass
    payloads = _parse_debug_records(caplog)
    assert any(p["event"] == "lock_timing" and p["lock_wait_ms"] >= 1 for p in payloads)


def test_sqlite_query_span_sets_row_count(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG, logger="application.bridge_timing")
    with sqlite_query_span("file_rows_page") as span:
        span.row_count = 50
        span.limit = 50
        span.offset = 0
    payloads = _parse_debug_records(caplog)
    assert payloads[0]["event"] == "sqlite_timing"
    assert payloads[0]["query_type"] == "file_rows_page"
    assert payloads[0]["row_count"] == 50


def test_phase_helpers(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG, logger="application.bridge_timing")
    t0 = log_phase_start("exact_index")
    time.sleep(0.01)
    log_phase_end("exact_index", t0, status="complete")
    payloads = _parse_debug_records(caplog)
    assert len(payloads) == 1
    assert payloads[0]["event"] == "phase_timing"
    assert payloads[0]["phase"] == "exact_index"
    assert payloads[0]["status"] == "complete"
    assert payloads[0]["elapsed_ms"] >= 1


def test_bridge_timing_decorator(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG, logger="application.bridge_timing")

    class _Api:
        @bridge_timing_decorator()
        def ping(self) -> str:
            return "pong"

    assert _Api().ping() == "pong"
    payloads = _timing_events(caplog, "bridge_timing")
    assert payloads[0]["method"] == "ping"


def test_bridge_api_methods_match_parity_and_are_wrapped() -> None:
    api_methods = {
        name
        for name in dir(BridgeApi)
        if not name.startswith("_") and callable(getattr(BridgeApi, name))
    }
    assert api_methods == set(PYWEBVIEW_API_METHODS)
    for name in PYWEBVIEW_API_METHODS:
        assert getattr(getattr(BridgeApi, name), "__wrapped__", None) is not None


def test_post_scan_worker_emits_phase_timing(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    lib = tmp_path / "lib"
    lib.mkdir()
    (lib / "a.txt").write_text("hello", encoding="utf-8")
    (lib / "b.txt").write_text("hello", encoding="utf-8")
    session = create_library_session(SqliteLibraryIndex(tmp_path / "phase.db"))
    session.select_folder(str(lib))
    api = create_bridge_api(session)
    api.start_scan()
    deadline = time.time() + 30
    while time.time() < deadline:
        snap = api.get_snapshot()
        if snap["work"]["scan"]["state"] in {"success", "error"}:
            if snap["pipeline"]["phase"] == "idle":
                break
        time.sleep(0.05)
    phases = {p["phase"] for p in _timing_events(caplog, "phase_timing")}
    assert "exact_index" in phases
    assert "worker" in phases or "queue" in phases


def test_query_file_rows_page_emits_sqlite_timing(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG)
    folder = tmp_path / "lib"
    folder.mkdir()
    (folder / "one.txt").write_text("x", encoding="utf-8")
    session = create_library_session(SqliteLibraryIndex(tmp_path / "sqlite.db"))
    session.select_folder(str(folder))
    api = create_bridge_api(session)
    api.start_scan()
    deadline = time.time() + 30
    while time.time() < deadline:
        snap = api.get_snapshot()
        if snap["work"]["scan"]["state"] in {"success", "error"}:
            if snap["pipeline"]["phase"] == "idle":
                break
        time.sleep(0.05)
    api.query_file_rows({"limit": 10})
    sqlite_events = _timing_events(caplog, "sqlite_timing")
    assert any(e["query_type"] == "file_rows_page" for e in sqlite_events)
