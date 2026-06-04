#!/usr/bin/env python3
"""Headless E2E: scan → approve exact dups → preview → apply (duplicate/ move)."""

from __future__ import annotations

import gc
import json
import shutil
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FOLDER = Path(r"F:\kiwi\text\test_folder")


def _scan_until_idle(api, timeout: float = 180.0) -> dict:
    deadline = time.monotonic() + timeout
    snap = api.get_snapshot()
    while time.monotonic() < deadline:
        if snap["work"]["scan"]["state"] == "running":
            time.sleep(0.1)
            snap = api.get_snapshot()
            continue
        if snap["pipeline"]["phase"] != "idle":
            time.sleep(0.1)
            snap = api.get_snapshot()
            continue
        break
    return snap


def _wait_deep_analysis(api, timeout: float = 300.0) -> dict:
    deadline = time.monotonic() + timeout
    snap = api.get_snapshot()
    while time.monotonic() < deadline:
        if snap["work"]["scan"]["deepAnalysisComplete"]:
            return snap
        if snap["work"]["scan"].get("deepAnalysisStatus") == "error":
            return snap
        time.sleep(0.1)
        snap = api.get_snapshot()
    return snap


def run_e2e(library_folder: Path, *, seed_exact_duplicate: bool) -> dict:
    if str(ROOT / "src") not in sys.path:
        sys.path.insert(0, str(ROOT / "src"))

    from app.session_factory import create_bridge_api, create_library_session
    from application.app_settings import AppSettings
    from application.settings_store import SettingsStore
    from infrastructure.memory_library_index import MemoryLibraryIndex

    report: dict = {"folder": str(library_folder), "steps": []}

    def step(name: str, ok: bool, **extra: object) -> None:
        report["steps"].append({"step": name, "ok": ok, **extra})

    settings_dir = tempfile.mkdtemp(prefix="ng-kiwi-settings-")
    try:
        settings = AppSettings(SettingsStore(Path(settings_dir) / "settings.json"))
        index = MemoryLibraryIndex()
        session = create_library_session(index, settings=settings)
        api = create_bridge_api(session)

        folder = str(library_folder.resolve())
        session.select_folder(folder)

        if seed_exact_duplicate:
            probe = library_folder / "ng_e2e_exact_dup_b.txt"
            source = next(library_folder.glob("*.txt"), None)
            if source is None:
                step("seed_duplicate", False, error="no .txt in folder")
                return report
            probe.write_bytes(source.read_bytes())
            step("seed_duplicate", True, source=source.name, probe=probe.name)

        api.start_scan()
        snap = _scan_until_idle(api)
        scan_ok = snap["work"]["scan"]["state"] == "success"
        step("scan", scan_ok, state=snap["work"]["scan"]["state"])

        snap = _wait_deep_analysis(api)
        deep_ok = bool(snap["work"]["scan"]["deepAnalysisComplete"])
        step(
            "deep_analysis",
            deep_ok,
            status=snap["work"]["scan"].get("deepAnalysisStatus"),
            error=snap["work"]["scan"].get("deepAnalysisError"),
        )

        page = api.query_review_rows({"viewMode": "all", "limit": 500})
        rows = page["rows"]
        by_type: dict[str, int] = {}
        for row in rows:
            t = str(row.get("type", "?"))
            by_type[t] = by_type.get(t, 0) + 1
        step("review_rows", True, total=len(rows), by_type=by_type)

        exact_move = [
            r
            for r in rows
            if r.get("type") == "exact" and r.get("proposedAction") == "move_duplicate"
        ]
        exact_groups = [r for r in rows if r.get("type") == "exact" and r.get("rowKind") == "group"]
        step("exact_move_candidates", True, count=len(exact_move), group_count=len(exact_groups))

        if not exact_move:
            report["status"] = "NO_EXACT_MOVE_ROWS"
            return report

        group_ids = {r["id"] for r in exact_groups}
        approve_ids = list(group_ids) if group_ids else [exact_move[0]["id"]]
        result = api.update_review_decisions(
            {"selection": {"type": "explicit_rows", "rowIds": approve_ids}, "command": "approve"}
        )
        step(
            "approve",
            result["updatedCount"] > 0,
            updatedCount=result["updatedCount"],
            approved_ids=len(approve_ids),
        )

        page2 = api.query_review_rows({"viewMode": "all", "limit": 500})
        approved_move = [
            r
            for r in page2["rows"]
            if r.get("proposedAction") == "move_duplicate" and r.get("status") == "approved"
        ]
        step("approved_rows", len(approved_move) > 0, count=len(approved_move))

        if not approved_move:
            report["status"] = "APPROVE_DID_NOT_STICK"
            return report

        sel = {"type": "explicit_rows", "rowIds": [approved_move[0]["id"]]}
        preview = api.get_move_preview(sel)
        step(
            "preview",
            preview.get("summary", {}).get("operationCount", 0) > 0,
            operationCount=preview.get("summary", {}).get("operationCount"),
        )

        move_row = approved_move[0]
        src_path = library_folder / str(move_row.get("path", move_row["name"]))
        src_exists_before = src_path.is_file()

        api.apply_resolved_actions(
            {"selection": sel, "previewToken": preview["previewToken"]}
        )
        dest_path = library_folder / "duplicate" / move_row["name"]
        moved = src_exists_before and not src_path.is_file() and dest_path.is_file()
        step(
            "apply_move",
            moved,
            src=str(src_path),
            dest=str(dest_path),
            src_exists_after=src_path.is_file(),
            dest_exists=dest_path.is_file(),
        )

        report["status"] = "PASS" if moved else "APPLY_FAILED"

        del api, session, index, settings
        gc.collect()
    finally:
        shutil.rmtree(settings_dir, ignore_errors=True)
    return report


def main() -> int:
    args = [a for a in sys.argv[1:] if a != "--seed-dup"]
    seed = "--seed-dup" in sys.argv
    folder = Path(args[0]) if args else DEFAULT_FOLDER
    if not folder.is_dir():
        print(json.dumps({"status": "FAIL", "error": f"not a directory: {folder}"}, indent=2))
        return 1

    work = folder
    if seed:
        work = Path(tempfile.mkdtemp(prefix="ng-kiwi-copy-"))
        shutil.copytree(folder, work, dirs_exist_ok=True)
        print(f"Working copy: {work}", file=sys.stderr)

    report = run_e2e(work, seed_exact_duplicate=seed)
    print(json.dumps(report, indent=2, ensure_ascii=False))

    if report.get("status") == "PASS":
        return 0
    if report.get("status") == "NO_EXACT_MOVE_ROWS" and not seed:
        print(
            "\nNo exact duplicate rows — re-run with --seed-dup to add a probe copy.",
            file=sys.stderr,
        )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
