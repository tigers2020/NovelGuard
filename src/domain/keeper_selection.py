"""Canonical keeper selection for duplicate groups (NOV-32 / NOV-33)."""

from __future__ import annotations

from domain.models import FileRecord


def pick_keeper_file_id(members: list[FileRecord]) -> str:
    if not members:
        raise ValueError("members must not be empty")
    keeper = max(members, key=lambda m: (m.size_bytes, m.modified_at_ns, m.relative_path))
    return keeper.id
