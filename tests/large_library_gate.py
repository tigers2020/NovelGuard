"""Helpers for the opt-in ~7.2k large-library performance gate."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "packaging" / "fixtures" / "library-large" / "manifest.json"
FULL_FIXTURE_DIR = ROOT / "packaging" / "fixtures" / "library-large" / "generated"
SMOKE_SCRIPT = ROOT / "scripts" / "large_library_loading_smoke.py"

# Keep in sync with scripts/large_library_loading_smoke.py SLO checks.
FILE_ROWS_P95_SLO_MS = 5000
REVIEW_ROWS_FIRST_SLO_MS = 10000


def expected_file_count() -> int:
    return int(json.loads(MANIFEST.read_text(encoding="utf-8"))["expected_file_count"])


def fixture_missing_reason() -> str | None:
    if not FULL_FIXTURE_DIR.is_dir():
        return f"fixture directory missing: {FULL_FIXTURE_DIR}"
    manifest_count = expected_file_count()
    actual = sum(1 for _ in FULL_FIXTURE_DIR.rglob("*.txt"))
    # Generator smoke allows >=7150; gate needs the full synthetic library.
    if actual < manifest_count - 50:
        return (
            f"fixture incomplete: {actual} .txt files "
            f"(expected ~{manifest_count}); "
            f"run: python scripts/generate_large_library_fixture.py"
        )
    return None


def require_full_fixture() -> Path:
    reason = fixture_missing_reason()
    if reason is None:
        return FULL_FIXTURE_DIR
    if os.environ.get("REQUIRE_LARGE_LIBRARY") == "1":
        pytest.fail(f"REQUIRE_LARGE_LIBRARY=1 set but {reason}")
    pytest.skip(reason)


def assert_slo_report(report: dict) -> None:
    timings = report.get("timings")
    if not isinstance(timings, dict):
        pytest.fail(f"large-library SLO gate missing timings in report: {report!r}")

    failures: list[str] = []
    file_rows_p95 = timings.get("query_file_rows_p95_ms")
    review_first = timings.get("query_review_rows_first_ms")

    if report.get("status") != "PASS":
        failures.append(f"smoke status={report.get('status')!r}")

    if not isinstance(file_rows_p95, (int, float)):
        failures.append("query_file_rows_p95_ms missing")
    elif file_rows_p95 > FILE_ROWS_P95_SLO_MS:
        failures.append(
            f"query_file_rows_p95_ms={file_rows_p95:.1f}ms exceeds "
            f"{FILE_ROWS_P95_SLO_MS}ms SLO"
        )

    if not isinstance(review_first, (int, float)):
        failures.append("query_review_rows_first_ms missing")
    elif review_first > REVIEW_ROWS_FIRST_SLO_MS:
        failures.append(
            f"query_review_rows_first_ms={review_first:.1f}ms exceeds "
            f"{REVIEW_ROWS_FIRST_SLO_MS}ms SLO"
        )

    if failures:
        timing_summary = json.dumps(timings, indent=2, sort_keys=True)
        pytest.fail(
            "large-library SLO gate failed:\n"
            + "\n".join(f"  - {item}" for item in failures)
            + f"\nTimings:\n{timing_summary}"
        )
