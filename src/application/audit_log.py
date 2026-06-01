"""Append-only JSONL audit log for apply operations."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any


class AuditLog:
    def __init__(self, path: Path, *, session_id: str | None = None) -> None:
        self._path = path
        self._session_id = session_id or sha256(str(path).encode("utf-8")).hexdigest()[:16]

    @property
    def path(self) -> Path:
        return self._path

    def append(self, event: str, **fields: Any) -> None:
        record: dict[str, Any] = {
            "ts": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "sessionId": self._session_id,
            "event": event,
            **fields,
        }
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
