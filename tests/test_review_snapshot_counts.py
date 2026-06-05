"""Unit tests for resolve snapshot count helpers (NOV-27 / NOV-25)."""

from __future__ import annotations

from application.review_snapshot_counts import file_row_status_counts, resolve_insight_counts


def _file_row(
    *,
    row_type: str = "exact",
    status: str = "unreviewed",
    row_kind: str = "file",
) -> dict[str, object]:
    return {"rowKind": row_kind, "type": row_type, "status": status}


def test_resolve_insight_counts_empty_rows() -> None:
    assert resolve_insight_counts([]) == (0, 0)


def test_resolve_insight_counts_splits_exact_from_near_and_relation() -> None:
    rows = [
        _file_row(row_type="exact"),
        _file_row(row_type="exact", status="conflict"),
        _file_row(row_type="near"),
        _file_row(row_type="relation"),
        _file_row(row_type="exact", status="approved"),
        _file_row(row_kind="group", row_type="near", status="unreviewed"),
    ]
    move_ready, review_signal = resolve_insight_counts(rows)
    queue, approved, conflict = file_row_status_counts(rows)

    assert move_ready == 2
    assert review_signal == 2
    assert move_ready + review_signal == queue
    assert approved == 1
    assert conflict == 1


def test_resolve_insight_counts_zero_when_no_unresolved_signals() -> None:
    rows = [
        _file_row(row_type="exact", status="approved"),
        _file_row(row_type="near", status="approved"),
    ]
    move_ready, review_signal = resolve_insight_counts(rows)
    queue, approved, conflict = file_row_status_counts(rows)

    assert move_ready == 0
    assert review_signal == 0
    assert queue == 0
    assert approved == 2
    assert conflict == 0


def test_resolve_insight_counts_ignores_excluded_rows() -> None:
    rows = [
        _file_row(row_type="exact", status="excluded"),
        _file_row(row_type="near", status="excluded"),
    ]
    assert resolve_insight_counts(rows) == (0, 0)
