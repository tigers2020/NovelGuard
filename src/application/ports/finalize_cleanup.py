"""Port for finalize empty-directory cleanup (PR-23)."""

from __future__ import annotations

from typing import Protocol

CLEANUP_ALLOWED_ROOT_NAMES = frozenset({"duplicate", "organized"})


class FinalizeCleanupPort(Protocol):
    def list_empty_dirs(self, library_root: str) -> list[str]:
        """Return library-relative paths of empty dirs under allowlisted roots."""

    def remove_empty_dirs(self, library_root: str, relative_paths: list[str]) -> list[str]:
        """Remove listed empty dirs; return paths actually removed."""
