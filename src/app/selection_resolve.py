"""Resolve SelectionScope to concrete review rows."""

from __future__ import annotations

from typing import Any

from app.bridge_contract import MAX_QUERY_LIMIT, EmptySelectionError, InvalidSelectionScopeError
from application.review_move_targets import collect_canonical_approved_move_target_rows
from application.review_query import _filter_rows, query_review_page
from application.review_state_merge import _file_id_from_row_id


def resolve_selection_rows(
    all_rows: list[dict[str, Any]],
    selection: dict[str, Any],
) -> list[dict[str, Any]]:
    scope_type = selection.get("type")
    if scope_type == "explicit_rows":
        row_ids = set(selection.get("rowIds") or [])
        if not row_ids:
            raise EmptySelectionError()
        return [row for row in all_rows if row.get("id") in row_ids]

    if scope_type == "current_query":
        query = selection.get("query")
        if not isinstance(query, dict) or not query.get("viewMode"):
            raise InvalidSelectionScopeError("current_query requires query.viewMode")
        exclude = set(selection.get("excludeRowIds") or [])
        page = query_review_page(all_rows, query, limit=MAX_QUERY_LIMIT)
        rows = [row for row in page["rows"] if row.get("id") not in exclude]
        if not rows:
            raise EmptySelectionError()
        return rows

    raise InvalidSelectionScopeError(f"Unknown SelectionScope type: {scope_type}")


def resolve_move_selection_rows(
    all_rows: list[dict[str, Any]],
    selection: dict[str, Any],
) -> list[dict[str, Any]]:
    """Resolve selection to deduped executable move rows (exact wins per file)."""
    scope_type = selection.get("type")
    if scope_type == "explicit_rows":
        row_ids = set(selection.get("rowIds") or [])
        if not row_ids:
            raise EmptySelectionError()
        picked = [row for row in all_rows if row.get("id") in row_ids]
        file_ids = {
            file_id
            for row in picked
            if (file_id := _file_id_from_row_id(str(row.get("id", ""))))
        }
        pool = [
            row
            for row in all_rows
            if (file_id := _file_id_from_row_id(str(row.get("id", "")))) and file_id in file_ids
        ]
        rows = collect_canonical_approved_move_target_rows(pool)
        if not rows:
            raise EmptySelectionError()
        return rows

    if scope_type == "current_query":
        query = selection.get("query")
        if not isinstance(query, dict) or not query.get("viewMode"):
            raise InvalidSelectionScopeError("current_query requires query.viewMode")
        exclude = set(selection.get("excludeRowIds") or [])
        move_query = dict(query)
        move_query["viewMode"] = "move"
        canonical = collect_canonical_approved_move_target_rows(all_rows)
        rows = [
            row
            for row in _filter_rows(canonical, move_query)
            if row.get("id") not in exclude
        ]
        if not rows:
            raise EmptySelectionError()
        return rows

    raise InvalidSelectionScopeError(f"Unknown SelectionScope type: {scope_type}")
