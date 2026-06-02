"""Domain types for PR-22 quality repair (UTF-8 rewrite)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

RepairAction = Literal["utf8_convert"]
EncodingConfidence = Literal["high", "low"]


@dataclass(frozen=True, slots=True)
class RepairOperation:
    issue_id: str
    file_id: str
    action: RepairAction
    relative_path: str
    source_encoding: str
    encoding_confidence: EncodingConfidence
    source_size: int
    source_content_hash: str
    source_mtime_ns: int | None = None
