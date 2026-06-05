"""Canonical keeper selection for duplicate groups (NOV-32 / NOV-33)."""

from __future__ import annotations

from domain.models import FileRecord


def pick_keeper_file_id(members: list[FileRecord]) -> str:
    """Pick keeper: size desc, mtime desc, path asc, file id asc."""
    if not members:
        raise ValueError("pick_keeper_file_id requires at least one member")
    keeper = max(
        members,
        key=lambda member: (
            member.size_bytes,
            member.modified_at_ns,
            member.relative_path,
            member.id,
        ),
    )
    return keeper.id
