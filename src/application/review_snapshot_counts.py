"""Aggregate review status counts for AppSnapshot (PR-17)."""

from __future__ import annotations

from typing import Any

from application.finalize_blockers import (
    exact_unresolved_queue_count,
    near_unresolved_file_row_count,
    relation_unresolved_file_row_count,
)


def resolve_insight_counts(rows: list[dict[str, Any]]) -> tuple[int, int]:
    """Return (move_ready_count, review_signal_count) for unresolved file rows."""
    move_ready = exact_unresolved_queue_count(rows)
    review_signal = near_unresolved_file_row_count(rows) + relation_unresolved_file_row_count(rows)
    return move_ready, review_signal


def file_row_status_counts(rows: list[dict[str, Any]]) -> tuple[int, int, int]:
    """Return (queue_count, approved_count, conflict_count) for file rows only."""
    queue = 0
    approved = 0
    conflict = 0
    for row in rows:
        if row.get("rowKind") != "file":
            continue
        status = row.get("status")
        if status == "approved":
            approved += 1
        elif status == "conflict":
            conflict += 1
        if status in ("unreviewed", "conflict"):
            queue += 1
    return queue, approved, conflict
