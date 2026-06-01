"""Canonical plan fingerprint for immutable preview operations."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from domain.apply_models import PreviewOperation


def preview_operation_to_dict(op: PreviewOperation) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "rowId": op.row_id,
        "action": op.action,
        "sourcePath": op.source_path,
        "destPath": op.dest_path,
        "sourceFileId": op.source_file_id,
        "sourceSize": op.source_size,
        "sourceContentHash": op.source_content_hash,
    }
    if op.source_mtime_ns is not None:
        payload["sourceMtimeNs"] = op.source_mtime_ns
    return payload


def preview_operations_from_dicts(items: list[dict[str, Any]]) -> list[PreviewOperation]:
    return [
        PreviewOperation(
            row_id=str(item["rowId"]),
            action="move_duplicate",
            source_path=str(item["sourcePath"]),
            dest_path=str(item["destPath"]),
            source_file_id=str(item["sourceFileId"]),
            source_size=int(item["sourceSize"]),
            source_content_hash=str(item["sourceContentHash"]),
            source_mtime_ns=(
                int(item["sourceMtimeNs"]) if item.get("sourceMtimeNs") is not None else None
            ),
        )
        for item in items
    ]


def plan_fingerprint(operations: list[PreviewOperation]) -> str:
    serialized = [preview_operation_to_dict(op) for op in operations]
    payload = json.dumps(serialized, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
