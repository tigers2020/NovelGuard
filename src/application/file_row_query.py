"""Normalize Shell FileDock queryFileRows payloads (PR-29)."""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from typing import Any, Literal, cast

from app.bridge_contract import (
    FILE_ROW_DEFAULT_QUERY_LIMIT,
    FILE_ROW_MAX_QUERY_LIMIT,
    FILE_ROW_SORT_FIELDS,
    FileRowQueryError,
)

DuplicateGroupFilter = Literal["any", "none"]
IntegrityFilter = Literal["ok", "issue", "unknown"]
SortDirection = Literal["asc", "desc"]

_VALID_DUPLICATE_GROUP = frozenset({"any", "none"})
_VALID_INTEGRITY = frozenset({"ok", "issue", "unknown"})


@dataclass(frozen=True)
class FileRowFilters:
    extensions: tuple[str, ...] | None = None
    encodings: tuple[str, ...] | None = None
    duplicate_group: DuplicateGroupFilter | None = None
    integrity: IntegrityFilter | None = None


@dataclass(frozen=True)
class NormalizedFileRowsQuery:
    search_term: str | None
    sort_field: str
    sort_direction: SortDirection
    filters: FileRowFilters
    cursor_offset: int
    limit: int
    wire_cursor: Any
    preset: str | None


def text_sort_key(value: str | None) -> str:
    normalized = "" if value is None else value
    return unicodedata.normalize("NFC", normalized).casefold()


def normalize_file_rows_query(raw_query: dict[str, Any]) -> NormalizedFileRowsQuery:
    sort_field, sort_direction = _parse_sort(raw_query)
    return NormalizedFileRowsQuery(
        search_term=_parse_search(raw_query.get("search")),
        sort_field=sort_field,
        sort_direction=sort_direction,
        filters=_parse_filters(raw_query.get("filters")),
        cursor_offset=_parse_cursor(raw_query.get("cursor")),
        limit=_parse_limit(raw_query.get("limit")),
        wire_cursor=raw_query.get("cursor"),
        preset=_parse_preset(raw_query.get("preset")),
    )


def _parse_search(search: Any) -> str | None:
    if not isinstance(search, str):
        return None
    stripped = search.strip()
    if not stripped:
        return None
    return text_sort_key(stripped)


def _parse_sort(raw_query: dict[str, Any]) -> tuple[str, SortDirection]:
    sort = raw_query.get("sort")
    if sort is None:
        return "path", "asc"
    if not isinstance(sort, dict):
        raise FileRowQueryError("INVALID_SORT_FIELD")
    field = sort.get("field")
    if not field:
        return "path", "asc"
    if not isinstance(field, str) or field not in FILE_ROW_SORT_FIELDS:
        raise FileRowQueryError("INVALID_SORT_FIELD")
    direction = sort.get("direction", "asc")
    if direction not in ("asc", "desc"):
        raise FileRowQueryError("INVALID_SORT_FIELD")
    return field, direction


def _parse_filters(raw_filters: Any) -> FileRowFilters:
    if raw_filters is None:
        return FileRowFilters()
    if not isinstance(raw_filters, dict):
        raise FileRowQueryError("INVALID_FILTER_VALUE")

    extensions = _parse_string_list_filter(raw_filters.get("extension"))
    encodings = _parse_string_list_filter(raw_filters.get("encoding"))
    duplicate_group = _parse_duplicate_group_filter(raw_filters.get("duplicateGroup"))
    integrity = _parse_integrity_filter(raw_filters.get("integrity"))

    unknown_keys = set(raw_filters.keys()) - {
        "extension",
        "encoding",
        "duplicateGroup",
        "integrity",
    }
    if unknown_keys:
        raise FileRowQueryError("INVALID_FILTER_VALUE")

    return FileRowFilters(
        extensions=extensions,
        encodings=encodings,
        duplicate_group=duplicate_group,
        integrity=integrity,
    )


def _parse_string_list_filter(raw: Any) -> tuple[str, ...] | None:
    if raw is None:
        return None
    if not isinstance(raw, list) or len(raw) == 0:
        raise FileRowQueryError("INVALID_FILTER_VALUE")
    keys: list[str] = []
    for item in raw:
        if not isinstance(item, str) or not item.strip():
            raise FileRowQueryError("INVALID_FILTER_VALUE")
        keys.append(text_sort_key(item.strip()))
    return tuple(keys)


def _parse_duplicate_group_filter(raw: Any) -> DuplicateGroupFilter | None:
    if raw is None:
        return None
    if not isinstance(raw, str) or raw not in _VALID_DUPLICATE_GROUP:
        raise FileRowQueryError("INVALID_FILTER_VALUE")
    return cast(DuplicateGroupFilter, raw)


def _parse_integrity_filter(raw: Any) -> IntegrityFilter | None:
    if raw is None:
        return None
    if not isinstance(raw, str) or raw not in _VALID_INTEGRITY:
        raise FileRowQueryError("INVALID_FILTER_VALUE")
    return cast(IntegrityFilter, raw)


def _parse_cursor(cursor: Any) -> int:
    if cursor is None:
        return 0
    try:
        return max(0, int(cursor))
    except (TypeError, ValueError):
        return 0


def _parse_limit(raw_limit: Any) -> int:
    if raw_limit is None:
        return FILE_ROW_DEFAULT_QUERY_LIMIT
    try:
        value = int(raw_limit)
    except (TypeError, ValueError):
        value = FILE_ROW_DEFAULT_QUERY_LIMIT
    return min(max(1, value), FILE_ROW_MAX_QUERY_LIMIT)


def _parse_preset(raw_preset: Any) -> str | None:
    if raw_preset is None:
        return None
    if not isinstance(raw_preset, str):
        return None
    return raw_preset
