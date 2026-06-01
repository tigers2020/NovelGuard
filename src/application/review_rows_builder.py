"""Build ReviewRow dicts from duplicate groups."""

from __future__ import annotations

from typing import Any

from domain.models import DuplicateGroup, FileRecord


def group_row_id(group_id: str) -> str:
    return f"group:{group_id}"


def member_row_id(group_id: str, file_id: str) -> str:
    return f"file:{group_id}:{file_id}"


def build_review_rows(
    groups: list[DuplicateGroup],
    files_by_id: dict[str, FileRecord],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for group in groups:
        members = [files_by_id[mid] for mid in group.member_ids if mid in files_by_id]
        if len(members) < 2:
            continue
        keeper = files_by_id.get(group.keeper_id) or members[0]
        representative = keeper.name
        rows.append(
            {
                "id": group_row_id(group.group_id),
                "rowKind": "group",
                "status": "unreviewed",
                "type": "exact",
                "name": representative,
                "keeperLabel": keeper.name,
                "proposedAction": "keep",
                "hasChildren": True,
                "groupId": group.group_id,
            }
        )
        for member in members:
            is_keeper = member.id == keeper.id
            rows.append(
                {
                    "id": member_row_id(group.group_id, member.id),
                    "rowKind": "file",
                    "status": "unreviewed",
                    "type": "exact",
                    "name": member.name,
                    "path": member.relative_path,
                    "sizeBytes": member.size_bytes,
                    "keeperLabel": keeper.name,
                    "proposedAction": "keep" if is_keeper else "move_duplicate",
                    "targetFolder": "duplicate/" if not is_keeper else None,
                    "hasChildren": False,
                    "groupId": group.group_id,
                }
            )
    return rows
