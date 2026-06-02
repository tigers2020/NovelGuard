"""In-memory file row page query (mock index + tests)."""

from __future__ import annotations

from typing import Any

from application.dto_mapper import empty_file_rows_page
from application.file_query import file_record_to_row
from application.file_row_query import NormalizedFileRowsQuery, text_sort_key
from domain.models import FileRecord


def query_file_rows_page_memory(
    files: list[FileRecord],
    normalized: NormalizedFileRowsQuery,
    *,
    projection_by_file_id: dict[str, tuple[str | None, bool]],
) -> dict[str, Any]:
    if not files:
        return empty_file_rows_page(normalized.wire_cursor)

    rows = [_enrich_row(file_record_to_row(record), projection_by_file_id.get(record.id)) for record in files]
    filtered = _apply_filters(rows, normalized)
    sorted_rows = _sort_rows(filtered, normalized)
    offset = normalized.cursor_offset
    limit = normalized.limit
    slice_rows = sorted_rows[offset : offset + limit]
    next_offset = offset + len(slice_rows)
    has_more = next_offset < len(sorted_rows)

    return {
        "rows": slice_rows,
        "pageInfo": {
            "cursor": normalized.wire_cursor,
            "nextCursor": str(next_offset) if has_more else None,
            "hasMore": has_more,
            "totalFiltered": len(filtered),
        },
    }


def _enrich_row(
    row: dict[str, Any],
    projection: tuple[str | None, bool] | None,
) -> dict[str, Any]:
    if projection is None:
        return row
    group_id, is_keeper = projection
    enriched = dict(row)
    enriched["duplicateGroupId"] = group_id
    enriched["isKeeper"] = is_keeper
    return enriched


def _apply_filters(rows: list[dict[str, Any]], normalized: NormalizedFileRowsQuery) -> list[dict[str, Any]]:
    filters = normalized.filters
    result = rows
    if normalized.search_term:
        term = normalized.search_term
        result = [
            row
            for row in result
            if term in text_sort_key(str(row.get("name", "")))
            or term in text_sort_key(str(row.get("path", "")))
            or term in text_sort_key(str(row.get("extension", "")))
        ]
    if filters.extensions:
        allowed = set(filters.extensions)
        result = [row for row in result if text_sort_key(str(row.get("extension", ""))) in allowed]
    if filters.encodings:
        allowed = set(filters.encodings)
        result = [
            row
            for row in result
            if text_sort_key(str(row.get("integrityStatus") or "")) in allowed
        ]
    if filters.duplicate_group == "any":
        result = [row for row in result if row.get("duplicateGroupId")]
    elif filters.duplicate_group == "none":
        result = [row for row in result if not row.get("duplicateGroupId")]
    if filters.integrity == "ok":
        result = [row for row in result if _integrity_bucket(row) == "ok"]
    elif filters.integrity == "unknown":
        result = [row for row in result if _integrity_bucket(row) == "unknown"]
    elif filters.integrity == "issue":
        result = [row for row in result if _integrity_bucket(row) == "issue"]
    return result


def _integrity_bucket(row: dict[str, Any]) -> str:
    status = row.get("integrityStatus")
    if status is None or status == "":
        return "unknown"
    key = text_sort_key(str(status))
    if key in ("utf-8", "ascii"):
        return "ok"
    return "issue"


def _sort_rows(rows: list[dict[str, Any]], normalized: NormalizedFileRowsQuery) -> list[dict[str, Any]]:
    field = normalized.sort_field
    reverse = normalized.sort_direction == "desc"

    def sort_key(row: dict[str, Any]) -> Any:
        if field == "size":
            return int(row.get("sizeBytes") or 0)
        if field == "modifiedAt":
            return str(row.get("modifiedAt") or "")
        if field == "duplicateGroup":
            group = row.get("duplicateGroupId")
            return text_sort_key(str(group)) if group else ""
        if field == "integrity":
            return text_sort_key(str(row.get("integrityStatus") or ""))
        if field == "encoding":
            return text_sort_key(str(row.get("integrityStatus") or ""))
        if field == "extension":
            return text_sort_key(str(row.get("extension", "")))
        if field == "name":
            return text_sort_key(str(row.get("name", "")))
        return text_sort_key(str(row.get("path", "")))

    ordered = sorted(rows, key=lambda row: (sort_key(row), str(row.get("id", ""))), reverse=reverse)
    if reverse:
        return ordered
    return ordered
