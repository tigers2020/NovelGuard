"""Build review rows for relation groups (PR-20)."""

from __future__ import annotations

from typing import Any

from domain.filename_relation import RelationGroup
from domain.keeper_selection import pick_keeper_record
from domain.models import FileRecord


def relation_group_row_id(group_id: str) -> str:
    return f"group:{group_id}"


def relation_member_row_id(group_id: str, file_id: str) -> str:
    return f"file:{group_id}:{file_id}"


def build_relation_review_rows(
    groups: list[RelationGroup],
    files_by_id: dict[str, FileRecord],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for group in groups:
        members = [files_by_id[mid] for mid in group.member_file_ids if mid in files_by_id]
        if len(members) < 2:
            continue
        keeper = pick_keeper_record(members)
        rows.append(
            {
                "id": relation_group_row_id(group.group_id),
                "rowKind": "group",
                "status": "unreviewed",
                "type": "relation",
                "name": keeper.name,
                "keeperLabel": keeper.name,
                "proposedAction": "keep",
                "hasChildren": True,
                "groupId": group.group_id,
                "relationKind": group.relation_kind,
                "confidence": group.confidence,
                "confidenceLabel": group.confidence_label,
            }
        )
        for member in members:
            is_keeper = member.id == keeper.id
            rows.append(
                {
                    "id": relation_member_row_id(group.group_id, member.id),
                    "rowKind": "file",
                    "status": "unreviewed",
                    "type": "relation",
                    "name": member.name,
                    "path": member.relative_path,
                    "sizeBytes": member.size_bytes,
                    "keeperLabel": keeper.name,
                    "proposedAction": "keep" if is_keeper else "move_duplicate",
                    "targetFolder": None if is_keeper else "duplicate/",
                    "hasChildren": False,
                    "groupId": group.group_id,
                    "relationKind": group.relation_kind,
                    "confidence": group.confidence,
                    "confidenceLabel": group.confidence_label,
                }
            )
    return rows
