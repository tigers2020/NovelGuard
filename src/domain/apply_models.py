"""Domain types for PR-15 real apply (preview plan + path policy)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ApplyAction = Literal["move_duplicate"]
PolicyBlockReason = Literal[
    "outside_root",
    "path_traversal",
    "absolute_path",
    "destination_exists",
    "unsupported_action",
    "invalid_target",
]


@dataclass(frozen=True, slots=True)
class PreviewOperation:
    row_id: str
    action: ApplyAction
    source_path: str
    dest_path: str
    source_file_id: str
    source_size: int
    source_content_hash: str
    source_mtime_ns: int | None = None


@dataclass(frozen=True, slots=True)
class PolicyResult:
    allowed: bool
    reason: PolicyBlockReason | None = None
