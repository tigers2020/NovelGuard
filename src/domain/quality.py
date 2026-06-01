"""Pure quality issue model (PR-14c)."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Literal

QualityKind = Literal["empty_file", "tiny_file", "invalid_utf8", "read_error"]
QualitySeverity = Literal["warning", "error"]


@dataclass(frozen=True, slots=True)
class QualityIssue:
    issue_id: str
    file_id: str
    path: str
    severity: QualitySeverity
    kind: QualityKind
    message: str
    evidence: dict[str, Any]


def make_issue_id(file_id: str, kind: QualityKind) -> str:
    payload = f"{file_id}|{kind}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
