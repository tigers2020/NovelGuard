"""Preflight counts and keeper row ids for auto-select keepers batch (NOV-33 / NOV-34)."""

from __future__ import annotations

from typing import Any

from application.review_query import query_review_page
from application.review_state_merge import _file_id_from_row_id
from domain.keeper_selection import pick_keeper_file_id
from domain.models import FileRecord

_MAX_TARGET = 500


def summarize_auto_select_keepers(
    all_rows: list[dict[str, Any]],
    query: dict[str, Any],
    *,
    files_by_id: dict[str, FileRecord],
    limit: int = _MAX_TARGET,
) -> dict[str, Any]:
    merged_filters: dict[str, Any] = {}
    raw_filters = query.get("filters")
    if isinstance(raw_filters, dict):
        merged_filters.update(raw_filters)
    merged_filters["status"] = ["unreviewed"]

    merged_query = {**query, "filters": merged_filters}

    file_rows: list[dict[str, Any]] = []
    offset = 0
    page_limit = min(200, limit)
    while len(file_rows) < limit:
        page_query = {**merged_query, "cursor": str(offset) if offset else None}
        page = query_review_page(all_rows, page_query, limit=page_limit)
        chunk = [
            row
            for row in page["rows"]
            if row.get("rowKind") == "file"
            and row.get("status") == "unreviewed"
            and row.get("status") != "conflict"
        ]
        file_rows.extend(chunk)
        if not page["pageInfo"].get("hasMore"):
            break
        next_cursor = page["pageInfo"].get("nextCursor")
        if next_cursor is None:
            break
        offset = int(next_cursor)

    file_rows = file_rows[:limit]

    by_group: dict[str, list[dict[str, Any]]] = {}
    for row in file_rows:
        group_id = row.get("groupId")
        if not isinstance(group_id, str):
            continue
        by_group.setdefault(group_id, []).append(row)

    keeper_row_ids: list[str] = []
    exact_count = 0
    near_count = 0
    relation_count = 0

    for group_rows in by_group.values():
        member_records: list[FileRecord] = []
        for row in group_rows:
            file_id = _file_id_from_row_id(str(row.get("id", "")))
            if file_id and file_id in files_by_id:
                member_records.append(files_by_id[file_id])
        if not member_records:
            continue

        keeper_id = pick_keeper_file_id(member_records)
        keeper_row = next(
            (
                row
                for row in group_rows
                if _file_id_from_row_id(str(row.get("id", ""))) == keeper_id
            ),
            None,
        )
        if keeper_row is not None:
            keeper_row_ids.append(str(keeper_row["id"]))

        row_type = str(group_rows[0].get("type", ""))
        group_size = len(group_rows)
        if row_type == "exact":
            exact_count += group_size
        elif row_type == "near":
            near_count += group_size
        elif row_type == "relation":
            relation_count += group_size

    keeper_count = len(keeper_row_ids)
    move_candidate_count = max(0, len(file_rows) - keeper_count)

    return {
        "targetCount": len(file_rows),
        "keeperCount": keeper_count,
        "moveCandidateCount": move_candidate_count,
        "exactCount": exact_count,
        "nearCount": near_count,
        "relationCount": relation_count,
        "keeperRowIds": keeper_row_ids,
    }
