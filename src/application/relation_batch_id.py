"""Relation detection batch identity (PR-20)."""

from __future__ import annotations

import hashlib

from domain.filename_relation import ALGORITHM_VERSION
from domain.models import FileRecord


def filename_set_digest(files: list[FileRecord]) -> str:
    lines = sorted(
        f"{record.id}|{record.name}|{record.size_bytes}|{record.modified_at_ns}" for record in files
    )
    payload = "\n".join(lines)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def make_relation_batch_id(
    *,
    library_revision: int,
    filename_set_digest_value: str,
    algorithm_version: str = ALGORITHM_VERSION,
) -> str:
    payload = f"{algorithm_version}:{library_revision}:{filename_set_digest_value[:16]}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
