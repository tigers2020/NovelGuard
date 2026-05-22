"""Integrity check result DTO."""

from dataclasses import dataclass

from application.dto.integrity_issue import IntegrityIssue


@dataclass(frozen=True)
class IntegrityCheckResult:
    """Per-file integrity check outcome."""

    file_id: int
    issues: list[IntegrityIssue]
    encoding: str | None
    encoding_confidence: float | None
