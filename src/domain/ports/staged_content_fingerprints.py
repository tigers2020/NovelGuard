"""Staged content fingerprints for exact duplicate detection (single-read I/O)."""

from dataclasses import dataclass


@dataclass(frozen=True)
class StagedContentFingerprints:
    """Prefix/suffix samples from one file open; optional full-file digest."""

    prefix_hash: str
    suffix_hash: str
    full_hash: str | None
