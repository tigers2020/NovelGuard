"""Integrity check request DTO."""

from dataclasses import dataclass


@dataclass(frozen=True)
class IntegrityCheckRequest:
    """Request to run integrity checks. None file_ids means all files in store."""

    file_ids: list[int] | None = None
