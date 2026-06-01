"""Pure domain models for library session (greenfield PR-14)."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DuplicateGroup:
    group_id: str
    member_ids: tuple[str, ...]
    keeper_id: str


@dataclass(frozen=True, slots=True)
class FileRecord:
    id: str
    relative_path: str
    name: str
    size_bytes: int
    modified_at_ns: int
    extension: str
    content_sha256: str | None = None
    encoding_status: str | None = None


def make_file_id(relative_posix_path: str, size_bytes: int, modified_at_ns: int) -> str:
    payload = f"{relative_posix_path}|{size_bytes}|{modified_at_ns}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
