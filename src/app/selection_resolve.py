"""Resolve SelectionScope to concrete review rows."""

from __future__ import annotations

from typing import Any

from app.bridge_contract import MAX_QUERY_LIMIT, EmptySelectionError, InvalidSelectionScopeError
from application.review_query import query_review_page


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
