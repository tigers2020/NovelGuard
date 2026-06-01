"""Filter, sort, and paginate review rows (mockData.ts semantics)."""

from __future__ import annotations

from typing import Any

from application.dto_mapper import empty_review_page

_NON_EXACT_TYPES = frozenset({"near", "relation", "move_only"})


def _types_yield_empty(query: dict[str, Any]) -> bool:
    types = (
        query.get("filters", {}).get("types") if isinstance(query.get("filters"), dict) else None
    )
    if not types:
        return False
    if not isinstance(types, list):
        return False
    if "exact" in types:
        return False
    return all(t in _NON_EXACT_TYPES for t in types)


def query_review_page(
    all_rows: list[dict[str, Any]],
    query: dict[str, Any],
    *,
    limit: int,
) -> dict[str, Any]:
    if _types_yield_empty(query):
        return empty_review_page()

    filtered = _filter_rows(all_rows, query)
    sorted_rows = _sort_rows(filtered, query)
    offset = _parse_cursor(query.get("cursor"))
    slice_rows = sorted_rows[offset : offset + limit]
    next_offset = offset + len(slice_rows)
    has_more = next_offset < len(sorted_rows)

    unreviewed = sum(1 for r in filtered if r.get("status") == "unreviewed")
    approved = sum(1 for r in filtered if r.get("status") == "approved")
    conflict = sum(1 for r in filtered if r.get("status") == "conflict")

    return {
        "rows": slice_rows,
        "pageInfo": {
            "cursor": query.get("cursor"),
            "nextCursor": str(next_offset) if has_more else None,
            "hasMore": has_more,
            "totalFiltered": len(filtered),
        },
        "summary": {
            "selectedCount": 0,
            "conflictCount": conflict,
            "unreviewedCount": unreviewed,
            "approvedCount": approved,
        },
    }


def _parse_cursor(cursor: Any) -> int:
    if cursor is None:
        return 0
    try:
        return max(0, int(cursor))
    except (TypeError, ValueError):
        return 0


def _filter_rows(rows: list[dict[str, Any]], query: dict[str, Any]) -> list[dict[str, Any]]:
    view_mode = query.get("viewMode", "all")
    raw_filters = query.get("filters")
    filters: dict[str, Any] = raw_filters if isinstance(raw_filters, dict) else {}
    search = (filters.get("search") or "").lower()
    status_filter = filters.get("status")
    type_filter = filters.get("types")

    result: list[dict[str, Any]] = []
    for row in rows:
        if row.get("type") != "exact":
            continue
        if view_mode == "conflicts" and row.get("status") != "conflict":
            continue
        if view_mode == "groups" and row.get("type") == "move_only":
            continue
        if view_mode == "move" and "move" not in str(row.get("proposedAction", "")):
            continue
        if view_mode == "action" and row.get("status") not in ("unreviewed", "conflict"):
            continue
        if status_filter and row.get("status") not in status_filter:
            continue
        if type_filter and row.get("type") not in type_filter:
            continue
        if search:
            haystack = (
                f"{row.get('name', '')} {row.get('keeperLabel', '')} "
                f"{row.get('targetFolder', '')} {row.get('type', '')}"
            ).lower()
            if search not in haystack:
                continue
        result.append(row)
    return result


def _sort_rows(rows: list[dict[str, Any]], query: dict[str, Any]) -> list[dict[str, Any]]:
    sort = query.get("sort")
    if not isinstance(sort, dict) or not sort.get("field"):
        return list(rows)
    field = sort["field"]
    direction = sort.get("direction", "asc")
    reverse = direction == "desc"

    def key(row: dict[str, Any]) -> Any:
        value = row.get(field)
        if value is None:
            return ""
        return value

    return sorted(rows, key=key, reverse=reverse)
