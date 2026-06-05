"""Auto-approve exact duplicate non-keepers after post-scan (NOV-17)."""

from __future__ import annotations

from application.ports.library_index import LibraryIndexPort, LoadedReviewState
from application.review_state_merge import _pick_keeper_id
from domain.duplicate_exact import find_exact_duplicate_groups
from domain.models import FileRecord


def persist_exact_non_keeper_approvals(
    folder: str,
    files: list[FileRecord],
    index: LibraryIndexPort,
    stored: LoadedReviewState,
) -> int:
    """Persist approved member_status for exact non-keepers without an existing member override."""
    files_by_id = {file_record.id: file_record for file_record in files}
    groups = find_exact_duplicate_groups(files)
    updated = 0

    for group in groups:
        group_entry = stored.groups.get(group.group_id)
        keeper_override = group_entry[0] if group_entry else None
        member_ids = [mid for mid in group.member_ids if mid in files_by_id]
        keeper_id = (
            keeper_override
            if keeper_override in member_ids
            else _pick_keeper_id(group, files_by_id)
        )

        for file_id in member_ids:
            if file_id == keeper_id:
                continue
            if file_id in stored.members:
                continue
            index.upsert_review_member(folder, file_id, "approved")
            updated += 1

    return updated
