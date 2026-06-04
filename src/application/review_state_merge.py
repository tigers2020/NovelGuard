"""Merge persisted review decisions into built review rows (PR-17)."""

from __future__ import annotations

from typing import Any

from application.ports.library_index import LoadedReviewState
from domain.duplicate_groups import find_duplicate_groups
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
            if isinstance(group_id, str) and (
                group_id.startswith("near:") or group_id.startswith("relation:")
            ):
                merged.append(_merge_non_exact_row(updated, group_id, stored, files_by_id))
            else:
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


def _merge_non_exact_row(
    row: dict[str, Any],
    group_id: str,
    stored: LoadedReviewState,
    files_by_id: dict[str, FileRecord],
) -> dict[str, Any]:
    updated = dict(row)
    group_entry = stored.groups.get(group_id)
    group_status = group_entry[1] if group_entry else None
    keeper_override = group_entry[0] if group_entry else None

    if row.get("rowKind") == "group":
        updated["status"] = group_status or row.get("status", "unreviewed")
        if keeper_override and keeper_override in files_by_id:
            updated["keeperLabel"] = files_by_id[keeper_override].name
        updated["proposedAction"] = "keep"
        return updated

    file_id = _file_id_from_row_id(str(row.get("id", "")))
    member_status = stored.members.get(file_id) if file_id else None
    if member_status:
        effective_status = member_status
    elif group_status:
        effective_status = group_status
    else:
        effective_status = row.get("status", "unreviewed")

    updated["status"] = effective_status
    if keeper_override and keeper_override in files_by_id:
        keeper = files_by_id[keeper_override]
        updated["keeperLabel"] = keeper.name
        updated["proposedAction"] = "keep" if file_id == keeper.id else "ignore"
    updated.pop("targetFolder", None)
    return updated


def _file_id_from_row_id(row_id: str) -> str | None:
    if not row_id.startswith("file:"):
        return None
    rest = row_id[5:]
    if len(rest) < 64:
        return None
    candidate = rest[-64:]
    if len(candidate) != 64:
        return None
    try:
        int(candidate, 16)
    except ValueError:
        return None
    return candidate


def group_id_from_row(row: dict[str, Any]) -> str | None:
    group_id = row.get("groupId")
    if isinstance(group_id, str):
        return group_id
    row_id = str(row.get("id", ""))
    if row_id.startswith("group:"):
        return row_id.split(":", 1)[1]
    if row_id.startswith("file:"):
        rest = row_id[5:]
        file_id = _file_id_from_row_id(row_id)
        if file_id and len(rest) > len(file_id) + 1:
            return rest[: -(len(file_id) + 1)]
    return None


def rebuild_rows_with_review_state(
    files: list[FileRecord],
    stored: LoadedReviewState,
    *,
    library_root: str | None = None,
) -> list[dict[str, Any]]:
    from pathlib import Path

    from application.review_rows_builder import build_review_rows

    files_by_id = {f.id: f for f in files}
    root = Path(library_root) if library_root else None
    groups = find_duplicate_groups(files, library_root=root)
    skeleton = build_review_rows(groups, files_by_id)
    return merge_review_state(
        skeleton,
        stored,
        groups=groups,
        files_by_id=files_by_id,
    )
