"""Near duplicate batch identity (PR-19)."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from domain.models import FileRecord


def content_set_digest(files: list[FileRecord]) -> str:
    lines = sorted(f"{record.id}:{record.content_sha256 or ''}" for record in files)
    payload = "\n".join(lines)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def make_near_batch_id(
    *,
    library_revision: int,
    folder_path: str,
    content_set_digest_value: str,
    scan_completed_at: str | None = None,
) -> str:
    _ = folder_path
    completed = scan_completed_at or datetime.now(timezone.utc).isoformat()
    digest_short = content_set_digest_value[:16]
    return f"{library_revision}:{completed}:{digest_short}"
