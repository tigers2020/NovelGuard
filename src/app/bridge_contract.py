"""Runtime bridge DTO validators (mirror web/src/contracts)."""

from __future__ import annotations

from typing import Any

FORBIDDEN_SNAPSHOT_ARRAY_KEYS = (
    "fileList",
    "reviewRows",
    "rows",
    "reviewRowsPage",
    "fileRows",
)

MAX_QUERY_LIMIT = 200
DEFAULT_QUERY_LIMIT = 100


class SnapshotContractError(ValueError):
    pass


class PageContractError(ValueError):
    pass


class EmptySelectionError(ValueError):
    pass


class InvalidSelectionScopeError(ValueError):
    pass


def validate_app_snapshot(snapshot: Any) -> None:
    if not isinstance(snapshot, dict):
        raise SnapshotContractError("AppSnapshot must be a dict")
    for key in (
        "route",
        "theme",
        "locale",
        "connection",
        "library",
        "pipeline",
        "work",
        "fileListSummary",
    ):
        if key not in snapshot:
            raise SnapshotContractError(f"AppSnapshot missing required field: {key}")
    for forbidden in FORBIDDEN_SNAPSHOT_ARRAY_KEYS:
        if forbidden in snapshot and isinstance(snapshot[forbidden], list):
            raise SnapshotContractError(f"AppSnapshot must not contain array field: {forbidden}")


def clamp_query_limit(query: dict[str, Any]) -> int:
    raw = int(query.get("limit") or DEFAULT_QUERY_LIMIT)
    return min(max(1, raw), MAX_QUERY_LIMIT)


def validate_review_rows_page(page: Any) -> None:
    if not isinstance(page, dict):
        raise PageContractError("ReviewRowsPage must be a dict")
    rows = page.get("rows")
    if not isinstance(rows, list) or len(rows) > MAX_QUERY_LIMIT:
        raise PageContractError("ReviewRowsPage.rows invalid or exceeds limit")
    if not isinstance(page.get("pageInfo"), dict) or not isinstance(page.get("summary"), dict):
        raise PageContractError("ReviewRowsPage.pageInfo or summary invalid")


def validate_quality_rows_page(page: Any) -> None:
    if not isinstance(page, dict):
        raise PageContractError("QualityRowsPage must be a dict")
    rows = page.get("rows")
    if not isinstance(rows, list) or len(rows) > MAX_QUERY_LIMIT:
        raise PageContractError("QualityRowsPage.rows invalid or exceeds limit")


def validate_move_preview(payload: Any) -> None:
    if not isinstance(payload, dict) or not isinstance(payload.get("rows"), list):
        raise PageContractError("Move preview must include rows array")


def validate_selection_scope(selection: Any) -> None:
    if not isinstance(selection, dict):
        raise InvalidSelectionScopeError("SelectionScope must be a dict")
    scope_type = selection.get("type")
    if scope_type == "explicit_rows":
        row_ids = selection.get("rowIds")
        if not isinstance(row_ids, list) or len(row_ids) == 0:
            raise EmptySelectionError()
        return
    if scope_type == "current_query":
        query = selection.get("query")
        if not isinstance(query, dict) or not query.get("viewMode"):
            raise InvalidSelectionScopeError(
                "current_query requires a ReviewRowsQuery with viewMode"
            )
        if not isinstance(selection.get("excludeRowIds"), list):
            raise InvalidSelectionScopeError("excludeRowIds must be an array")
        return
    raise InvalidSelectionScopeError(f"Unknown SelectionScope type: {scope_type}")
