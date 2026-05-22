"""Pre-flight counts for a full pipeline run (GUI aggregation only).

Used by ``WorkTab`` before ``PipelineRunConfirmSheet`` (rev. 3.9 auto-only).
Also covered by ``tests/gui/services/test_pipeline_run_preview.py``.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from application.use_cases.move_duplicate_files import MoveDuplicateFilesUseCase
from application.use_cases.organize_by_chosung import OrganizeByChosungUseCase
from application.utils.duplicate_json import find_latest_duplicate_summary
from gui.models.file_data_store import FileDataStore

if TYPE_CHECKING:
    from application.ports.log_sink import ILogSink


@dataclass(frozen=True)
class PipelineRunPreview:
    """Summary shown before one-shot pipeline approval."""

    folder_path: str | None
    total_files: int
    duplicate_groups: int
    duplicate_move_count: int
    organize_dry_run_total: int
    error_message: str | None = None
    duplicate_groups_from_cache: bool = False
    cached_detection_timestamp: str | None = None


def _count_duplicate_groups(store: FileDataStore) -> int:
    group_ids = {
        f.duplicate_group_id for f in store.get_all_files() if f.duplicate_group_id is not None
    }
    return len(group_ids)


def compute_pipeline_run_preview(
    store: FileDataStore,
    *,
    scan_folder: Optional[Path],
    log_sink: Optional[ILogSink] = None,
) -> PipelineRunPreview:
    """Compute dry-run move counts for the run confirm sheet."""
    folder = scan_folder or store.scan_folder
    all_files = store.get_all_files()
    store_groups = _count_duplicate_groups(store)
    cached_summary = (
        find_latest_duplicate_summary(folder) if folder is not None and folder.is_dir() else None
    )

    duplicate_groups = store_groups
    groups_from_cache = False
    cached_ts: str | None = None
    if store_groups == 0 and cached_summary is not None:
        duplicate_groups = cached_summary.total_groups
        groups_from_cache = True
        cached_ts = cached_summary.detection_timestamp

    dup_count = 0
    org_total = 0
    err: str | None = None

    if folder is not None and folder.is_dir():
        try:
            ops = MoveDuplicateFilesUseCase(store, log_sink).execute(folder)
            dup_count = len(ops)
        except Exception as exc:
            err = str(exc)
        if dup_count == 0 and cached_summary is not None and store_groups == 0:
            dup_count = cached_summary.duplicate_move_count
        try:
            org_result = OrganizeByChosungUseCase(log_sink=log_sink).execute(
                root_path=folder,
                move=True,
                dry_run=True,
            )
            org_total = org_result.total_processed
        except Exception as exc:
            err = err or str(exc)

    return PipelineRunPreview(
        folder_path=str(folder) if folder else None,
        total_files=len(all_files),
        duplicate_groups=duplicate_groups,
        duplicate_move_count=dup_count,
        organize_dry_run_total=org_total,
        error_message=err,
        duplicate_groups_from_cache=groups_from_cache,
        cached_detection_timestamp=cached_ts,
    )
