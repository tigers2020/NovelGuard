"""Full-filter dry-run summary for resolve bulk auto-approve (spec 035 slice 1)."""

from __future__ import annotations

from typing import Any

from application.review_query import query_review_page
from application.review_state_merge import _file_id_from_row_id
from domain.keeper_selection import pick_keeper_file_id
from domain.models import FileRecord

_PAGE_LIMIT = 200
_MAX_SAMPLES = 5
_ELIGIBLE_TYPES = frozenset({"exact", "near", "relation"})


def _merge_unreviewed_query(query: dict[str, Any]) -> dict[str, Any]:
    merged_filters: dict[str, Any] = {}
    raw_filters = query.get("filters")
    if isinstance(raw_filters, dict):
        merged_filters.update(raw_filters)
    merged_filters["status"] = ["unreviewed"]
    return {**query, "filters": merged_filters, "cursor": None}


def _stream_file_rows(
    all_rows: list[dict[str, Any]],
    query: dict[str, Any],
    *,
    status_filter: list[str] | None = None,
) -> list[dict[str, Any]]:
    merged_filters: dict[str, Any] = {}
    raw_filters = query.get("filters")
    if isinstance(raw_filters, dict):
        merged_filters.update(raw_filters)
    if status_filter is not None:
        merged_filters["status"] = status_filter
    merged_query = {**query, "filters": merged_filters, "cursor": None}

    collected: list[dict[str, Any]] = []
    offset = 0
    while True:
        page_query = {**merged_query, "cursor": str(offset) if offset else None}
        page = query_review_page(all_rows, page_query, limit=_PAGE_LIMIT)
        chunk = [
            row
            for row in page["rows"]
            if row.get("rowKind") == "file"
            and row.get("type") in _ELIGIBLE_TYPES
            and row.get("status") != "conflict"
        ]
        collected.extend(chunk)
        if not page["pageInfo"].get("hasMore"):
            break
        next_cursor = page["pageInfo"].get("nextCursor")
        if next_cursor is None:
            break
        offset = int(next_cursor)
    return collected


def summarize_resolve_auto_approve(
    all_rows: list[dict[str, Any]],
    query: dict[str, Any],
    *,
    files_by_id: dict[str, FileRecord],
    members_by_group: dict[str, set[str]],
) -> dict[str, Any]:
    """Server dry-run: full filter scan, no mutation, no public 500 cap."""
    unreviewed_query = _merge_unreviewed_query(query)
    file_rows = _stream_file_rows(all_rows, unreviewed_query)

    skipped_rows = _stream_file_rows(
        all_rows,
        query,
        status_filter=["conflict", "excluded"],
    )
    skipped_conflict_count = sum(1 for row in skipped_rows if row.get("status") == "conflict")
    skipped_excluded_count = sum(1 for row in skipped_rows if row.get("status") == "excluded")

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
    sample_keepers: list[str] = []
    sample_move_candidates: list[str] = []
    sample_exact: list[str] = []
    sample_near: list[str] = []
    sample_relation: list[str] = []

    for group_id, group_rows in by_group.items():
        member_ids = members_by_group.get(group_id, set())
        member_records = [
            files_by_id[member_id] for member_id in member_ids if member_id in files_by_id
        ]
        if not member_records:
            member_records = []
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
            _append_sample(sample_keepers, str(keeper_row.get("name", "")))

        row_type = str(group_rows[0].get("type", ""))
        group_size = len(group_rows)
        if row_type == "exact":
            exact_count += group_size
            for row in group_rows:
                _append_sample(sample_exact, str(row.get("name", "")))
        elif row_type == "near":
            near_count += group_size
            for row in group_rows:
                _append_sample(sample_near, str(row.get("name", "")))
        elif row_type == "relation":
            relation_count += group_size
            for row in group_rows:
                _append_sample(sample_relation, str(row.get("name", "")))

        for row in group_rows:
            if keeper_row is not None and str(row["id"]) == str(keeper_row["id"]):
                continue
            _append_sample(sample_move_candidates, str(row.get("name", "")))

    keeper_count = len(keeper_row_ids)
    unreviewed_count = len(file_rows)
    move_candidate_count = max(0, unreviewed_count - keeper_count)

    return {
        "unreviewedCount": unreviewed_count,
        "keeperCount": keeper_count,
        "moveCandidateCount": move_candidate_count,
        "exactCount": exact_count,
        "nearCount": near_count,
        "relationCount": relation_count,
        "skippedConflictCount": skipped_conflict_count,
        "skippedExcludedCount": skipped_excluded_count,
        "keeperRowIds": keeper_row_ids,
        "samples": {
            "keepers": sample_keepers[:_MAX_SAMPLES],
            "moveCandidates": sample_move_candidates[:_MAX_SAMPLES],
            "exact": sample_exact[:_MAX_SAMPLES],
            "near": sample_near[:_MAX_SAMPLES],
            "relation": sample_relation[:_MAX_SAMPLES],
        },
    }


def _append_sample(bucket: list[str], name: str) -> None:
    if not name or len(bucket) >= _MAX_SAMPLES:
        return
    if name in bucket:
        return
    bucket.append(name)
