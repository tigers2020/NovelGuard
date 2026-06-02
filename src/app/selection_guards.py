"""Selection guards for preview/apply (PR-19)."""

from __future__ import annotations

from typing import Any


def selection_includes_near_rows(rows: list[dict[str, Any]]) -> bool:
    return any(row.get("type") == "near" for row in rows)
