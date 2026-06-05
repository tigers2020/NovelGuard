#!/usr/bin/env python3
"""Headless large-library loading smoke. Pattern: scripts/fixture_library_smoke.py."""

from __future__ import annotations

import argparse
import json
import logging
import statistics
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FIXTURE = ROOT / "packaging" / "fixtures" / "library-large" / "generated"


def _wait_index_ready(api, timeout: float = 300.0) -> dict:
    deadline = time.monotonic() + timeout
    snap = api.get_snapshot()
    while time.monotonic() < deadline:
        if snap["work"]["scan"].get("indexReady"):
            return snap
        time.sleep(0.1)
        snap = api.get_snapshot()
    raise TimeoutError("indexReady not set")


def _wait_scan_success(api, timeout: float = 600.0) -> dict:
    deadline = time.monotonic() + timeout
    snap = api.get_snapshot()
    while time.monotonic() < deadline:
        if snap["work"]["scan"].get("state") == "success":
            return snap
        if snap["work"]["scan"].get("state") == "error":
            raise RuntimeError(f"scan failed: {snap['work']['scan']}")
        time.sleep(0.1)
        snap = api.get_snapshot()
    raise TimeoutError("scan did not reach success")


def _timed(call) -> tuple[object, float]:
    t0 = time.perf_counter()
    result = call()
    return result, (time.perf_counter() - t0) * 1000.0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--folder", type=Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--skip-generate", action="store_true")
    args = parser.parse_args()

    if not args.skip_generate and not args.folder.exists():
        subprocess.check_call([sys.executable, str(ROOT / "scripts" / "generate_large_library_fixture.py")])

    if str(ROOT / "src") not in sys.path:
        sys.path.insert(0, str(ROOT / "src"))

    logging.basicConfig(level=logging.DEBUG)

    from app.session_factory import create_bridge_api, create_library_session
    from application.app_settings import AppSettings
    from application.settings_store import SettingsStore
    from infrastructure.sqlite_library_index import SqliteLibraryIndex
    import tempfile

    timings: dict[str, float] = {}
    timing_events: list[str] = []

    class _TimingCapture(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            msg = record.getMessage()
            if '"event":' in msg and any(
                key in msg
                for key in ('"bridge_timing"', '"lock_wait"', '"sqlite_query"', '"post_scan_phase"')
            ):
                timing_events.append(msg)

    handler = _TimingCapture()
    logging.getLogger().addHandler(handler)

    with tempfile.TemporaryDirectory(prefix="ng-large-smoke-") as tmp:
        settings = AppSettings(SettingsStore(Path(tmp) / "settings.json"))
        index = SqliteLibraryIndex(Path(tmp) / "library.db")
        session = create_library_session(index, settings=settings)
        api = create_bridge_api(session)
        folder = str(args.folder.resolve())
        session.select_folder(folder)
        api.start_scan()
        index_ready_at = time.perf_counter()
        _wait_index_ready(api)
        timings["index_ready_ms"] = (time.perf_counter() - index_ready_at) * 1000.0
        _wait_scan_success(api)

        file_samples: list[float] = []
        for _ in range(5):
            _, ms = _timed(lambda: api.query_file_rows({"limit": 100, "cursor": None}))
            file_samples.append(ms)
        timings["query_file_rows_p95_ms"] = statistics.quantiles(file_samples, n=20)[-1]

        _, review_ms = _timed(
            lambda: api.query_review_rows({"viewMode": "all", "limit": 100, "cursor": None})
        )
        timings["query_review_rows_first_ms"] = review_ms

    report = {
        "status": "PASS",
        "timings": timings,
        "timing_event_kinds": sorted(
            {
                json.loads(event).get("event")
                for event in timing_events
                if event.startswith("{")
            }
        ),
    }
    slo_fail = (
        timings["query_file_rows_p95_ms"] > 5000
        or timings["query_review_rows_first_ms"] > 10000
    )
    if slo_fail:
        report["status"] = "FAIL"
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
