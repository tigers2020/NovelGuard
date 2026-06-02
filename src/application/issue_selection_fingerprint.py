"""SHA-256 fingerprint of normalized quality repair issue id selection."""

from __future__ import annotations

import hashlib
import json

from application.quality_issue_detail import normalize_quality_issue_id

MAX_REPAIR_BATCH = 10


def normalize_repair_issue_ids(issue_ids: list[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for raw in issue_ids:
        if not isinstance(raw, str):
            continue
        resolved = normalize_quality_issue_id(raw)
        if resolved is None or resolved in seen:
            continue
        seen.add(resolved)
        normalized.append(resolved)
    normalized.sort()
    return normalized


def issue_selection_fingerprint(issue_ids: list[str]) -> str:
    normalized = normalize_repair_issue_ids(issue_ids)
    payload = json.dumps({"issueIds": normalized}, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
