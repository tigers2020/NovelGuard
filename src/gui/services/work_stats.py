"""Work-screen statistics from FileDataStore (GUI aggregation only)."""

from application.constants import Constants
from gui.models.file_data_store import FileDataStore
from gui.view_models.work_dto import WorkStats


def compute_work_stats(file_data_store: FileDataStore) -> WorkStats:
    """Compute metrics shared by header and work summary strip."""
    all_files = file_data_store.get_all_files()

    total_files = len(all_files)
    processed_files = sum(1 for f in all_files if f.duplicate_group_id is not None)

    saved_bytes = sum(
        f.size for f in all_files if f.duplicate_group_id is not None and not f.is_canonical
    )
    saved_gb = saved_bytes / Constants.BYTES_PER_GB

    duplicate_group_ids = {
        f.duplicate_group_id for f in all_files if f.duplicate_group_id is not None
    }
    duplicate_groups = len(duplicate_group_ids)

    total_bytes = sum(f.size for f in all_files)
    total_size_gb = total_bytes / Constants.BYTES_PER_GB

    integrity_issues = sum(1 for f in all_files if f.integrity_severity in ("ERROR", "WARN"))

    duplicate_files = sum(
        1 for f in all_files if f.duplicate_group_id is not None and not f.is_canonical
    )

    small_files = sum(1 for f in all_files if f.size < Constants.SMALL_FILE_THRESHOLD)

    return WorkStats(
        total_files=total_files,
        duplicate_groups=duplicate_groups,
        saved_gb=saved_gb,
        integrity_issues=integrity_issues,
        processed_files=processed_files,
        duplicate_files=duplicate_files,
        total_size_gb=total_size_gb,
        small_files=small_files,
    )
