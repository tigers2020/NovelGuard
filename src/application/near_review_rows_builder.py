"""Build review rows for near duplicate groups (PR-19)."""

from __future__ import annotations

from typing import Any

from domain.duplicate_near import NearDuplicateGroup
from domain.keeper_selection import pick_keeper_file_id
from domain.models import FileRecord


def near_group_row_id(group_id: str) -> str:
    return f"group:{group_id}"


def near_member_row_id(group_id: str, file_id: str) -> str:
    return f"file:{group_id}:{file_id}"


def build_near_review_rows(
    groups: list[NearDuplicateGroup],
    files_by_id: dict[str, FileRecord],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for group in groups:
        members = [files_by_id[mid] for mid in group.member_file_ids if mid in files_by_id]
        if len(members) < 2:
            continue
        keeper_id = pick_keeper_file_id(members)
        keeper = next(member for member in members if member.id == keeper_id)
        rows.append(
            {
                "id": near_group_row_id(group.group_id),
                "rowKind": "group",
                "status": "unreviewed",
                "type": "near",
                "name": keeper.name,
                "keeperLabel": keeper.name,
                "proposedAction": "keep",
                "hasChildren": True,
                "groupId": group.group_id,
                "confidence": group.max_similarity,
            }
        )
        for member in members:
            rows.append(
                {
                    "id": near_member_row_id(group.group_id, member.id),
                    "rowKind": "file",
                    "status": "unreviewed",
                    "type": "near",
                    "name": member.name,
                    "path": member.relative_path,
                    "sizeBytes": member.size_bytes,
                    "keeperLabel": keeper.name,
                    "proposedAction": "keep" if member.id == keeper_id else "move_duplicate",
                    "targetFolder": None if member.id == keeper_id else "duplicate/",
                    "hasChildren": False,
                    "groupId": group.group_id,
                    "confidence": group.max_similarity,
                }
            )
    return rows
