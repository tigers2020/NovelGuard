"""Aggregate review status counts for AppSnapshot (PR-17)."""

from __future__ import annotations

from typing import Any


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
