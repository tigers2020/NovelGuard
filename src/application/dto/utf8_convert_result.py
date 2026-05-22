"""UTF-8 conversion result DTO."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Utf8ConvertResult:
    """Batch UTF-8 conversion summary."""

    converted: int
    skipped: int
    failed: int
    errors: list[str]
