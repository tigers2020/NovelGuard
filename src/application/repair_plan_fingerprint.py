"""Canonical repair plan fingerprint (PR-22)."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from domain.repair_models import RepairOperation


def repair_operation_to_dict(op: RepairOperation) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "issueId": op.issue_id,
        "fileId": op.file_id,
        "action": op.action,
        "relativePath": op.relative_path,
        "sourceEncoding": op.source_encoding,
        "encodingConfidence": op.encoding_confidence,
        "sourceSize": op.source_size,
        "sourceContentHash": op.source_content_hash,
    }
    if op.source_mtime_ns is not None:
        payload["sourceMtimeNs"] = op.source_mtime_ns
    return payload


def repair_plan_fingerprint(operations: list[RepairOperation]) -> str:
    serialized = [repair_operation_to_dict(op) for op in operations]
    payload = json.dumps(serialized, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
