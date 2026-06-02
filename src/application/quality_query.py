"""Filter, sort, and paginate quality rows (mockBridge.ts semantics)."""

from __future__ import annotations

import unicodedata
from typing import Any

from app.bridge_contract import QUALITY_SORT_FIELDS, QualityQueryError
from application.dto_mapper import empty_quality_page

_VALID_ISSUE_TYPES = frozenset({"integrity", "encoding", "small_file"})
_SEVERITY_ORDINAL = {"error": 0, "warning": 1}


def query_quality_page(
    all_rows: list[dict[str, Any]],
    query: dict[str, Any],
    *,
    limit: int,
) -> dict[str, Any]:
    issue_type = query.get("issueType")
    if issue_type not in _VALID_ISSUE_TYPES:
        return empty_quality_page()

    filtered = _filter_rows(all_rows, query, issue_type=str(issue_type))
    sorted_rows = _sort_rows(filtered, query)
    offset = _parse_cursor(query.get("cursor"))
    slice_rows = sorted_rows[offset : offset + limit]
    next_offset = offset + len(slice_rows)
    has_more = next_offset < len(sorted_rows)

    warning = sum(1 for r in filtered if r.get("severity") == "warning")
    error = sum(1 for r in filtered if r.get("severity") == "error")

    return {
        "rows": slice_rows,
        "pageInfo": {
            "cursor": query.get("cursor"),
            "nextCursor": str(next_offset) if has_more else None,
            "hasMore": has_more,
            "totalFiltered": len(filtered),
        },
        "summary": {
            "issueCount": len(filtered),
            "warningCount": warning,
            "errorCount": error,
        },
    }


def _parse_cursor(cursor: Any) -> int:
    if cursor is None:
        return 0
    try:
        return max(0, int(cursor))
    except (TypeError, ValueError):
        return 0


def _filter_rows(
    rows: list[dict[str, Any]],
    query: dict[str, Any],
    *,
    issue_type: str,
) -> list[dict[str, Any]]:
    raw_filters = query.get("filters")
    filters: dict[str, Any] = raw_filters if isinstance(raw_filters, dict) else {}
    search = (filters.get("search") or "").lower()
    severity_filter = filters.get("severity")

    result: list[dict[str, Any]] = []
    for row in rows:
        if row.get("issueType") != issue_type:
            continue
        if severity_filter and row.get("severity") != severity_filter:
            continue
        if search:
            haystack = (
                f"{row.get('name', '')} {row.get('path', '')} "
                f"{row.get('integrity', '')} {row.get('message', '')}"
            ).lower()
            if search not in haystack:
                continue
        result.append(row)
    return result


def _text_sort_key(value: Any) -> str:
    if not isinstance(value, str):
        value = "" if value is None else str(value)
    return unicodedata.normalize("NFC", value).casefold()


def _validate_sort_field(query: dict[str, Any]) -> None:
    sort = query.get("sort")
    if not isinstance(sort, dict):
        return
    field = sort.get("field")
    if not field:
        return
    if field not in QUALITY_SORT_FIELDS:
        raise QualityQueryError("INVALID_SORT_FIELD")


def _sort_rows(rows: list[dict[str, Any]], query: dict[str, Any]) -> list[dict[str, Any]]:
    _validate_sort_field(query)
    sort = query.get("sort")
    if not isinstance(sort, dict) or not sort.get("field"):
        return list(rows)

    field = str(sort["field"])
    reverse = sort.get("direction", "asc") == "desc"

    def primary_key(row: dict[str, Any]) -> Any:
        if field == "severity":
            severity = row.get("severity")
            ordinal = _SEVERITY_ORDINAL.get(severity, 99) if isinstance(severity, str) else 99
            return -ordinal
        return _text_sort_key(row.get(field))

    indexed = list(enumerate(rows))
    indexed.sort(
        key=lambda pair: (primary_key(pair[1]), pair[0], str(pair[1].get("id", ""))),
        reverse=reverse,
    )
    return [row for _, row in indexed]
