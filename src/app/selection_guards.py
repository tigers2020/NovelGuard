"""Selection guards for preview/apply (PR-19 / PR-20)."""

from __future__ import annotations

from typing import Any


def selection_includes_near_rows(rows: list[dict[str, Any]]) -> bool:
    return any(row.get("type") == "near" for row in rows)


def selection_includes_relation_rows(rows: list[dict[str, Any]]) -> bool:
    return any(row.get("type") == "relation" for row in rows)


def first_blocking_review_row_type(rows: list[dict[str, Any]]) -> str | None:
    if any(row.get("type") == "near" for row in rows):
        return "near"
    if any(row.get("type") == "relation" for row in rows):
        return "relation"
    return None
