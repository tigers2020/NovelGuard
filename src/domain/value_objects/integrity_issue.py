"""Integrity issue value object (domain)."""

from dataclasses import dataclass
from enum import StrEnum


class IntegrityRuleId(StrEnum):
    """Integrity rule identifiers."""

    EMPTY_FILE = "EMPTY_FILE"
    SMALL_FILE = "SMALL_FILE"
    ENCODING_UNKNOWN = "ENCODING_UNKNOWN"
    ENCODING_NON_UTF8 = "ENCODING_NON_UTF8"
    DECODE_ERROR = "DECODE_ERROR"


@dataclass(frozen=True)
class IntegrityIssue:
    """Single integrity finding for a file."""

    rule_id: IntegrityRuleId
    message: str
    severity: str
