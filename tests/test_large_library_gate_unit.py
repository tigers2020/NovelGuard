"""Unit checks for large-library gate helpers (no 7k fixture required)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from large_library_gate import (
    FILE_ROWS_P95_SLO_MS,
    REVIEW_ROWS_FIRST_SLO_MS,
    assert_slo_report,
    require_full_fixture,
)


def test_assert_slo_report_passes_on_valid_report() -> None:
    assert_slo_report(
        {
            "status": "PASS",
            "timings": {
                "query_file_rows_p95_ms": FILE_ROWS_P95_SLO_MS,
                "query_review_rows_first_ms": REVIEW_ROWS_FIRST_SLO_MS,
            },
        }
    )


def test_assert_slo_report_fails_with_clear_slo_message() -> None:
    report = {
        "status": "FAIL",
        "timings": {
            "query_file_rows_p95_ms": FILE_ROWS_P95_SLO_MS + 1,
            "query_review_rows_first_ms": 100,
        },
    }
    with pytest.raises(pytest.fail.Exception) as exc:
        assert_slo_report(report)
    message = exc.value.msg
    assert "large-library SLO gate failed" in message
    assert "query_file_rows_p95_ms" in message
    assert str(FILE_ROWS_P95_SLO_MS) in message
    assert json.dumps(report["timings"], indent=2) in message


def test_require_full_fixture_fails_when_required_and_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("REQUIRE_LARGE_LIBRARY", "1")
    monkeypatch.setattr("large_library_gate.FULL_FIXTURE_DIR", tmp_path / "missing")
    with pytest.raises(pytest.fail.Exception):
        require_full_fixture()
