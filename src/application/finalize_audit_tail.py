"""Read apply/repair audit tail for finalize summary (PR-23)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_MOVE_APPLY_EVENTS = frozenset({"apply_row", "apply_completed"})
_REPAIR_APPLY_EVENTS = frozenset({"repair_applied", "repair_completed"})


def read_audit_tail(path: Path, *, limit: int = 50) -> dict[str, Any]:
    if not path.is_file():
        return {
            "lastMoveApplyAt": None,
            "lastRepairApplyAt": None,
            "moveApplyCount": 0,
            "repairApplyCount": 0,
        }
    lines: list[str] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if stripped:
                lines.append(stripped)
    tail = lines[-limit:] if len(lines) > limit else lines

    move_apply_count = 0
    repair_apply_count = 0
    last_move_at: str | None = None
    last_repair_at: str | None = None

    for line in tail:
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(record, dict):
            continue
        event = record.get("event")
        ts = record.get("ts")
        if not isinstance(event, str):
            continue
        if event in _MOVE_APPLY_EVENTS:
            move_apply_count += 1
            if isinstance(ts, str):
                last_move_at = ts
        if event in _REPAIR_APPLY_EVENTS:
            repair_apply_count += 1
            if isinstance(ts, str):
                last_repair_at = ts

    return {
        "lastMoveApplyAt": last_move_at,
        "lastRepairApplyAt": last_repair_at,
        "moveApplyCount": move_apply_count,
        "repairApplyCount": repair_apply_count,
    }
