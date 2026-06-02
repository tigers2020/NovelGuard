"""Merge persisted review decisions into built review rows (PR-17)."""

from __future__ import annotations

from typing import Any

from application.ports.library_index import LoadedReviewState
from domain.duplicate_exact import find_exact_duplicate_groups
from domain.models import DuplicateGroup, FileRecord


def _pick_keeper_id(group: DuplicateGroup, files_by_id: dict[str, FileRecord]) -> str:
    members = [files_by_id[mid] for mid in group.member_ids if mid in files_by_id]
    if not members:
        return group.keeper_id
    keeper = max(members, key=lambda m: (m.size_bytes, m.relative_path))
    return keeper.id


def merge_review_state(
    rows: list[dict[str, Any]],
    stored: LoadedReviewState,
    *,
    groups: list[DuplicateGroup],
    files_by_id: dict[str, FileRecord],
) -> list[dict[str, Any]]:
    members_by_group = {g.group_id: g for g in groups}
    merged: list[dict[str, Any]] = []

    for row in rows:
        updated = dict(row)
        group_id = row.get("groupId")
        if not isinstance(group_id, str):
            merged.append(updated)
            continue

        group_entry = stored.groups.get(group_id)
        keeper_override = group_entry[0] if group_entry else None
        group_status = group_entry[1] if group_entry else None

        group = members_by_group.get(group_id)
        if group is None:
            merged.append(updated)
            continue

        member_ids = [mid for mid in group.member_ids if mid in files_by_id]
        keeper_id = (
            keeper_override
            if keeper_override in member_ids
            else _pick_keeper_id(group, files_by_id)
        )
        keeper = files_by_id[keeper_id]

        if row.get("rowKind") == "group":
            updated["status"] = group_status or "unreviewed"
            updated["keeperLabel"] = keeper.name
            updated["proposedAction"] = "keep"
            merged.append(updated)
            continue

        if row.get("rowKind") != "file":
            merged.append(updated)
            continue

        file_id = _file_id_from_row_id(str(row.get("id", "")))
        member_status = stored.members.get(file_id) if file_id else None
        if member_status:
            effective_status = member_status
        elif group_status:
            effective_status = group_status
        else:
            effective_status = "unreviewed"

        is_keeper = file_id == keeper_id
        updated["status"] = effective_status
        updated["keeperLabel"] = keeper.name
        updated["proposedAction"] = "keep" if is_keeper else "move_duplicate"
        updated["targetFolder"] = None if is_keeper else "duplicate/"
        merged.append(updated)

    return merged


def _file_id_from_row_id(row_id: str) -> str | None:
    if not row_id.startswith("file:"):
        return None
    parts = row_id.split(":", 2)
    if len(parts) != 3:
        return None
    return parts[2]


def group_id_from_row(row: dict[str, Any]) -> str | None:
    group_id = row.get("groupId")
    if isinstance(group_id, str):
        return group_id
    row_id = str(row.get("id", ""))
    if row_id.startswith("group:"):
        return row_id.split(":", 1)[1]
    if row_id.startswith("file:"):
        parts = row_id.split(":", 2)
        if len(parts) == 3:
            return parts[1]
    return None


def rebuild_rows_with_review_state(
    files: list[FileRecord],
    stored: LoadedReviewState,
) -> list[dict[str, Any]]:
    from application.review_rows_builder import build_review_rows

    files_by_id = {f.id: f for f in files}
    groups = find_exact_duplicate_groups(files)
    skeleton = build_review_rows(groups, files_by_id)
    return merge_review_state(
        skeleton,
        stored,
        groups=groups,
        files_by_id=files_by_id,
    )
