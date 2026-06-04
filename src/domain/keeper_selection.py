"""Default keeper selection for duplicate / near / relation groups.

Priority (highest first):
1. ``size_bytes`` — larger file wins
2. ``relative_path`` — lexicographic tie-break (spec 005)
3. ``modified_at_ns`` — stable last resort only
"""

from __future__ import annotations

from domain.models import FileRecord


def pick_keeper_record(members: list[FileRecord]) -> FileRecord:
    if not members:
        raise ValueError("pick_keeper_record requires at least one member")
    return max(members, key=lambda m: (m.size_bytes, m.relative_path, m.modified_at_ns))
