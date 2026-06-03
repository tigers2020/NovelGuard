#!/usr/bin/env python3
"""Headless beta smoke on packaging/fixtures/library (no GUI)."""

from __future__ import annotations

import json
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "packaging" / "fixtures" / "library"


def _scan_until_idle(api, timeout: float = 60.0) -> dict:
    deadline = time.monotonic() + timeout
    snap = api.get_snapshot()
    while time.monotonic() < deadline:
        if snap["work"]["scan"]["state"] == "running":
            time.sleep(0.05)
            snap = api.get_snapshot()
            continue
        if snap["pipeline"]["phase"] != "idle":
            time.sleep(0.05)
            snap = api.get_snapshot()
            continue
        break
    return snap


def _wait_deep_analysis(api, timeout: float = 120.0) -> dict:
    deadline = time.monotonic() + timeout
    snap = api.get_snapshot()
    while time.monotonic() < deadline:
        if snap["work"]["scan"]["deepAnalysisComplete"]:
            return snap
        if snap["work"]["scan"]["deepAnalysisStatus"] == "error":
            return snap
        time.sleep(0.05)
        snap = api.get_snapshot()
    return snap


def main() -> int:
    if str(ROOT / "src") not in sys.path:
        sys.path.insert(0, str(ROOT / "src"))

    from app.bridge_contract import validate_app_snapshot, validate_review_rows_page
    from app.session_factory import create_bridge_api, create_library_session
    from application.app_settings import AppSettings
    from application.settings_store import SettingsStore
    from infrastructure.sqlite_library_index import SqliteLibraryIndex

    if not FIXTURE.is_dir():
        print(f"FAIL: missing fixture {FIXTURE}")
        return 1

    results: dict[str, str] = {}
    with tempfile.TemporaryDirectory(prefix="ng-fixture-smoke-") as tmp:
        settings = AppSettings(SettingsStore(Path(tmp) / "settings.json"))
        index = SqliteLibraryIndex(Path(tmp) / "library.db")
        session = create_library_session(index, settings=settings)
        api = create_bridge_api(session)

        folder = str(FIXTURE.resolve())
        session.select_folder(folder)
        api.start_scan()
        snap = _scan_until_idle(api)
        if snap["work"]["scan"]["state"] != "success":
            print(json.dumps({"fail": "scan", "state": snap["work"]["scan"]["state"]}, indent=2))
            return 1
        results["scan"] = "PASS"

        snap = _wait_deep_analysis(api)
        if snap["work"]["scan"]["deepAnalysisStatus"] == "error":
            print(
                json.dumps(
                    {"fail": "deep_analysis", "error": snap["work"]["scan"]["deepAnalysisError"]}
                )
            )
            return 1
        if not snap["work"]["scan"]["deepAnalysisComplete"]:
            print("FAIL: deep analysis timeout")
            return 1
        results["deep_analysis"] = "PASS"

        validate_app_snapshot(snap)
        fc = snap["library"]["fileCount"]
        dg = snap["library"]["duplicateGroups"]
        if fc < 4:
            print(f"FAIL: fileCount={fc} expected >= 4")
            return 1
        if dg < 1:
            print(f"FAIL: duplicateGroups={dg} expected >= 1 (alpha/alpha-copy)")
            return 1
        results["snapshot"] = f"PASS files={fc} dup_groups={dg}"

        review = api.query_review_rows({"viewMode": "groups", "limit": 50})
        validate_review_rows_page(review)
        results["review_rows"] = f"PASS rows={len(review['rows'])}"

        info = api.get_app_info()
        if info.get("buildType") not in ("dev", "packaged"):
            print(f"FAIL: buildType={info.get('buildType')}")
            return 1
        results["app_info"] = "PASS"

    print(json.dumps({"status": "PASS", "checks": results}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
