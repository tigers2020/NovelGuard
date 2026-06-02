"""Filter and paginate library file rows for Shell FileDock (PR-25 v1)."""

from __future__ import annotations

from typing import Any

from application.dto_mapper import empty_file_rows_page
from application.file_row_query import text_sort_key
from domain.models import FileRecord


def file_record_to_row(record: FileRecord) -> dict[str, Any]:
    return {
        "id": record.id,
        "name": record.name,
        "path": record.relative_path,
        "sizeBytes": record.size_bytes,
        "modifiedAt": _modified_iso(record.modified_at_ns),
        "extension": record.extension,
        "duplicateGroupId": None,
        "isKeeper": None,
        "integrityStatus": record.encoding_status,
    }


def _modified_iso(modified_at_ns: int) -> str:
    from datetime import UTC, datetime

    seconds = modified_at_ns / 1_000_000_000
    return datetime.fromtimestamp(seconds, tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def query_file_page(
    all_rows: list[dict[str, Any]],
    query: dict[str, Any],
    *,
    limit: int,
) -> dict[str, Any]:
    if not all_rows:
        return empty_file_rows_page(query.get("cursor"))

    filtered = _filter_rows(all_rows, query)
    sorted_rows = sorted(filtered, key=lambda row: str(row.get("path", "")))
    offset = _parse_cursor(query.get("cursor"))
    slice_rows = sorted_rows[offset : offset + limit]
    next_offset = offset + len(slice_rows)
    has_more = next_offset < len(sorted_rows)

    return {
        "rows": slice_rows,
        "pageInfo": {
            "cursor": query.get("cursor"),
            "nextCursor": str(next_offset) if has_more else None,
            "hasMore": has_more,
            "totalFiltered": len(filtered),
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
    search = query.get("search")
    if not isinstance(search, str) or not search.strip():
        return rows
    term = text_sort_key(search.strip())
    result: list[dict[str, Any]] = []
    for row in rows:
        name = text_sort_key(str(row.get("name", "")))
        path = text_sort_key(str(row.get("path", "")))
        ext = text_sort_key(str(row.get("extension", "")))
        if term in name or term in path or term in ext:
            result.append(row)
    return result
