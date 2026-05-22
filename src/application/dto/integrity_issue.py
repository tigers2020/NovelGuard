"""Integrity issue DTO (application boundary)."""

from dataclasses import dataclass


@dataclass(frozen=True)
class IntegrityIssue:
    """Single integrity finding exposed to GUI and workers."""

    rule_id: str
    message: str
    severity: str
