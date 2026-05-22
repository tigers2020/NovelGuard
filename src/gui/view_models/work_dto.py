"""DTOs for work screen summary (GUI layer only)."""

from dataclasses import dataclass
from typing import Literal

LibraryState = Literal["idle", "previewing", "scanning", "ready"]
DuplicateState = Literal["idle", "running", "ready", "empty"]


@dataclass(frozen=True)
class WorkStats:
    """Aggregated file-store metrics."""

    total_files: int
    duplicate_groups: int
    saved_gb: float
    integrity_issues: int
    processed_files: int
    duplicate_files: int
    total_size_gb: float
    small_files: int


@dataclass(frozen=True)
class WorkSummary:
    """Summary strip snapshot."""

    folder_path: str | None
    total_files: int
    duplicate_groups: int
    saved_gb: float
    integrity_issues: int
    library_state: LibraryState
    duplicate_state: DuplicateState
