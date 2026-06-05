"""Unit tests for resolve snapshot lane counts (NOV-27 / NOV-25)."""

from __future__ import annotations

from application.review_snapshot_counts import resolve_insight_counts


def _file_row(
    *,
    row_type: str = "exact",
    status: str = "unreviewed",
    row_kind: str = "file",
) -> dict:
    return {
        "rowKind": row_kind,
        "type": row_type,
        "status": status,
    }


def test_resolve_insight_counts_empty_rows() -> None:
    assert resolve_insight_counts([]) == (0, 0)


def test_resolve_insight_counts_splits_exact_near_relation() -> None:
    rows = [
        _file_row(row_type="exact", status="unreviewed"),
        _file_row(row_type="exact", status="conflict"),
        _file_row(row_type="near", status="unreviewed"),
        _file_row(row_type="relation", status="conflict"),
        _file_row(row_type="exact", status="approved"),
        _file_row(row_type="near", status="approved"),
        _file_row(row_kind="group", row_type="exact", status="unreviewed"),
    ]
    move_ready, review_signal = resolve_insight_counts(rows)
    assert move_ready == 2
    assert review_signal == 2


def test_resolve_insight_counts_ignores_excluded_rows() -> None:
    rows = [
        _file_row(row_type="exact", status="excluded"),
        _file_row(row_type="near", status="excluded"),
    ]
    assert resolve_insight_counts(rows) == (0, 0)
