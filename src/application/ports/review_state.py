"""Review persistence types (PR-17)."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class LoadedReviewState:
    """group_id -> (keeper_file_id | None, group_status | None); file_id -> member_status."""

    groups: dict[str, tuple[str | None, str | None]] = field(default_factory=dict)
    members: dict[str, str] = field(default_factory=dict)
