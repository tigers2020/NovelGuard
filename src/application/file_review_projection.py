"""Build 1:1 file_review_projection rows from merged review cache (PR-29)."""

from __future__ import annotations

from typing import Any

from application.file_row_query import text_sort_key
from application.review_state_merge import _file_id_from_row_id

_TYPE_RANK = {"exact": 0, "near": 1, "relation": 2}


def build_file_review_projection(
    review_rows_cache: list[dict[str, Any]],
) -> list[tuple[str, str | None, bool, str | None]]:
    """Return (file_id, duplicate_group_id, is_keeper, duplicate_group_key) per file."""
    winners: dict[str, tuple[int, str, bool, str]] = {}

    for row in review_rows_cache:
        if row.get("rowKind") != "file":
            continue
        file_id = _file_id_from_row_id(str(row.get("id", "")))
        if not file_id:
            continue
        group_id = row.get("groupId")
        if not isinstance(group_id, str):
            continue
        row_type = str(row.get("type", "exact"))
        type_rank = _TYPE_RANK.get(row_type, 99)
        is_keeper = row.get("proposedAction") == "keep"
        group_key = text_sort_key(group_id)
        candidate = (type_rank, group_id, is_keeper, group_key)
        current = winners.get(file_id)
        if current is None or (type_rank, group_id) < (current[0], current[1]):
            winners[file_id] = candidate

    return [
        (file_id, group_id, is_keeper, group_key)
        for file_id, (_, group_id, is_keeper, group_key) in winners.items()
    ]
