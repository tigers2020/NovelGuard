"""SHA-256 fingerprint of normalized SelectionScope (mirror web/src/bridge/selectionFingerprint.ts)."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def _normalize_review_rows_query(query: dict[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {
        "viewMode": query["viewMode"],
        "filters": query.get("filters") or {},
        "cursor": query.get("cursor"),
        "limit": query.get("limit") if query.get("limit") is not None else 100,
    }
    if query.get("sort") is not None:
        normalized["sort"] = query["sort"]
    return normalized


def normalize_selection_scope(selection: dict[str, Any]) -> dict[str, Any]:
    scope_type = selection.get("type")
    if scope_type == "explicit_rows":
        row_ids = selection.get("rowIds") or []
        return {"type": "explicit_rows", "rowIds": sorted(row_ids)}
    if scope_type == "current_query":
        query = selection.get("query") or {}
        exclude = selection.get("excludeRowIds") or []
        return {
            "type": "current_query",
            "query": _normalize_review_rows_query(query),
            "excludeRowIds": sorted(exclude),
        }
    raise ValueError(f"Unknown SelectionScope type: {scope_type}")


def selection_fingerprint(selection: dict[str, Any]) -> str:
    normalized = normalize_selection_scope(selection)
    payload = json.dumps(normalized, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
