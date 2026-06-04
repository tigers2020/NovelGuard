"""Exact duplicate detection (size + content SHA-256)."""

from __future__ import annotations

from collections import defaultdict

from domain.keeper_selection import pick_keeper_record
from domain.models import DuplicateGroup, FileRecord


def find_exact_duplicate_groups(files: list[FileRecord]) -> list[DuplicateGroup]:
    """Group files with identical size and content_sha256 (count >= 2)."""
    by_size: dict[int, list[FileRecord]] = defaultdict(list)
    for record in files:
        if record.content_sha256 is None:
            continue
        by_size[record.size_bytes].append(record)

    groups: list[DuplicateGroup] = []
    for size_bucket in by_size.values():
        by_hash: dict[str, list[FileRecord]] = defaultdict(list)
        for record in size_bucket:
            by_hash[record.content_sha256 or ""].append(record)
        for content_hash, members in by_hash.items():
            if len(members) < 2 or not content_hash:
                continue
            keeper = _pick_keeper(members)
            group_id = f"dup-{content_hash[:16]}"
            groups.append(
                DuplicateGroup(
                    group_id=group_id,
                    member_ids=tuple(m.id for m in members),
                    keeper_id=keeper.id,
                )
            )
    return groups


def _pick_keeper(members: list[FileRecord]) -> FileRecord:
    return pick_keeper_record(members)
