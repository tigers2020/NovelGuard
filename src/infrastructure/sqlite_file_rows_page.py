"""SQLite paginated queryFileRows (PR-29)."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from typing import Any

from application.dto_mapper import empty_file_rows_page
from application.file_row_query import NormalizedFileRowsQuery

_SORT_COLUMNS = {
    "name": "f.name_key",
    "path": "f.relative_path_key",
    "extension": "f.extension_key",
    "size": "f.size_bytes",
    "modifiedAt": "f.modified_at_ns",
    "encoding": "f.encoding_key",
    "integrity": "f.encoding_key",
    "duplicateGroup": "p.duplicate_group_key",
}


def _modified_iso(modified_at_ns: int) -> str:
    seconds = modified_at_ns / 1_000_000_000
    return datetime.fromtimestamp(seconds, tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _like_pattern(term: str) -> str:
    escaped = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def _build_where(
    folder_path: str,
    normalized: NormalizedFileRowsQuery,
) -> tuple[str, list[Any]]:
    clauses = ["f.folder_path = ?"]
    params: list[Any] = [folder_path]

    if normalized.search_term:
        pattern = _like_pattern(normalized.search_term)
        clauses.append(
            "(f.name_key LIKE ? ESCAPE '\\' OR f.relative_path_key LIKE ? ESCAPE '\\' "
            "OR f.extension_key LIKE ? ESCAPE '\\')"
        )
        params.extend([pattern, pattern, pattern])

    filters = normalized.filters
    if filters.extensions:
        placeholders = ",".join("?" for _ in filters.extensions)
        clauses.append(f"f.extension_key IN ({placeholders})")
        params.extend(filters.extensions)
    if filters.encodings:
        placeholders = ",".join("?" for _ in filters.encodings)
        clauses.append(f"f.encoding_key IN ({placeholders})")
        params.extend(filters.encodings)
    if filters.duplicate_group == "any":
        clauses.append("p.duplicate_group_id IS NOT NULL")
    elif filters.duplicate_group == "none":
        clauses.append("p.duplicate_group_id IS NULL")
    if filters.integrity == "ok":
        clauses.append("f.encoding_key IN ('utf-8', 'ascii')")
    elif filters.integrity == "unknown":
        clauses.append("(f.encoding_status IS NULL OR f.encoding_status = '')")
    elif filters.integrity == "issue":
        clauses.append(
            "(f.encoding_status IS NOT NULL AND f.encoding_status != '' "
            "AND f.encoding_key NOT IN ('utf-8', 'ascii'))"
        )

    return " AND ".join(clauses), params


def _order_by(normalized: NormalizedFileRowsQuery) -> str:
    column = _SORT_COLUMNS.get(normalized.sort_field, "f.relative_path_key")
    direction = "DESC" if normalized.sort_direction == "desc" else "ASC"
    if normalized.sort_field == "duplicateGroup":
        nulls = "NULLS LAST" if normalized.sort_direction == "asc" else "NULLS FIRST"
        return f"{column} {direction} {nulls}, f.id ASC"
    return f"{column} {direction}, f.id ASC"


def query_sqlite_file_rows_page(
    conn: sqlite3.Connection,
    folder_path: str,
    normalized: NormalizedFileRowsQuery,
) -> dict[str, Any]:
    where_sql, where_params = _build_where(folder_path, normalized)
    base_from = """
        FROM files f
        LEFT JOIN file_review_projection p
          ON f.folder_path = p.folder_path AND f.id = p.file_id
    """
    count_row = conn.execute(
        f"SELECT COUNT(*) {base_from} WHERE {where_sql}",
        where_params,
    ).fetchone()
    total_filtered = int(count_row[0]) if count_row else 0

    if total_filtered == 0:
        return empty_file_rows_page(normalized.wire_cursor)

    order_sql = _order_by(normalized)
    rows = conn.execute(
        f"""
        SELECT
          f.id,
          f.name,
          f.relative_path,
          f.size_bytes,
          f.modified_at_ns,
          f.extension,
          f.encoding_status,
          p.duplicate_group_id,
          p.is_keeper
        {base_from}
        WHERE {where_sql}
        ORDER BY {order_sql}
        LIMIT ? OFFSET ?
        """,
        (*where_params, normalized.limit, normalized.cursor_offset),
    ).fetchall()

    wire_rows = [
        {
            "id": row[0],
            "name": row[1],
            "path": row[2],
            "sizeBytes": row[3],
            "modifiedAt": _modified_iso(int(row[4])),
            "extension": row[5],
            "duplicateGroupId": row[7],
            "isKeeper": bool(row[8]) if row[7] is not None else False,
            "integrityStatus": row[6],
        }
        for row in rows
    ]
    offset = normalized.cursor_offset
    next_offset = offset + len(wire_rows)
    has_more = next_offset < total_filtered

    return {
        "rows": wire_rows,
        "pageInfo": {
            "cursor": normalized.wire_cursor,
            "nextCursor": str(next_offset) if has_more else None,
            "hasMore": has_more,
            "totalFiltered": total_filtered,
        },
    }
