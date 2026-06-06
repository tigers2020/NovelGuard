"""Read recovery / undo manifest state for bridge getRecoveryState."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from application.recovery_store import JsonlRecoveryStore

ACTIVE_MANIFEST_STATUSES = frozenset({"pending", "partial", "executing"})


def empty_recovery_state() -> dict[str, Any]:
    return {
        "hasActivePlan": False,
        "undoPlanId": None,
        "runId": None,
        "batchKind": None,
        "manifestStatus": None,
        "appliedCount": 0,
        "recoverableCount": 0,
        "manualRequiredCount": 0,
        "blockedCount": 0,
        "unrecoverableCount": 0,
        "sealedAt": None,
    }


def _read_manifest_file(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    return payload


def find_active_undo_manifest(
    store: JsonlRecoveryStore,
    *,
    library_id: str,
) -> dict[str, Any] | None:
    candidates: list[tuple[str, dict[str, Any]]] = []
    for path in store.list_undo_manifest_files():
        payload = _read_manifest_file(path)
        if payload is None:
            continue
        if payload.get("libraryId") != library_id:
            continue
        status = payload.get("status")
        if status not in ACTIVE_MANIFEST_STATUSES:
            continue
        sealed_at = payload.get("sealedAt")
        if not isinstance(sealed_at, str) or not sealed_at.strip():
            continue
        candidates.append((sealed_at, payload))
    if not candidates:
        return None
    candidates.sort(key=lambda item: item[0], reverse=True)
    return candidates[0][1]


def build_recovery_state(
    *,
    store: JsonlRecoveryStore,
    library_id: str,
) -> dict[str, Any]:
    manifest = find_active_undo_manifest(store, library_id=library_id)
    if manifest is None:
        return empty_recovery_state()

    summary = manifest.get("summary")
    if not isinstance(summary, dict):
        summary = {}

    return {
        "hasActivePlan": True,
        "undoPlanId": manifest.get("undoPlanId"),
        "runId": manifest.get("runId"),
        "batchKind": manifest.get("sourceBatchKind"),
        "manifestStatus": manifest.get("status"),
        "appliedCount": int(summary.get("appliedCount", 0)),
        "recoverableCount": int(summary.get("recoverableCount", 0)),
        "manualRequiredCount": int(summary.get("manualCount", 0)),
        "blockedCount": 0,
        "unrecoverableCount": int(summary.get("unrecoverableCount", 0)),
        "sealedAt": manifest.get("sealedAt"),
    }
