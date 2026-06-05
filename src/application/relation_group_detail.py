"""Build DuplicateGroupDetail for relation groups (PR-20)."""

from __future__ import annotations

from typing import Any

from application.duplicate_group_detail import member_integrity
from application.review_state_merge import _file_id_from_row_id
from domain.filename_relation import RelationGroup
from domain.keeper_selection import pick_keeper_file_id
from domain.models import FileRecord

_NOT_FOUND_MESSAGE = "Group not found. Refresh the review list."
_REVIEW_STATUSES = frozenset({"unreviewed", "approved", "conflict", "excluded"})


def build_relation_group_detail(
    group_id: str,
    *,
    relation_group: RelationGroup | None,
    review_rows: list[dict[str, Any]],
    files_by_id: dict[str, FileRecord],
    quality_by_path: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    gid = group_id.strip()
    if relation_group is None or relation_group.group_id != gid:
        return {
            "status": "not_found",
            "groupId": gid,
            "members": [],
            "message": _NOT_FOUND_MESSAGE,
        }

    group_rows = [row for row in review_rows if row.get("groupId") == gid]
    file_rows = [row for row in group_rows if row.get("rowKind") == "file"]
    if not file_rows:
        return {
            "status": "not_found",
            "groupId": gid,
            "members": [],
            "message": _NOT_FOUND_MESSAGE,
        }

    members: list[dict[str, Any]] = []
    for row in file_rows:
        row_id = str(row.get("id", ""))
        file_id = _file_id_from_row_id(row_id)
        if not file_id:
            continue
        record = files_by_id.get(file_id)
        if record is None:
            continue
        proposed = row.get("proposedAction", "ignore")
        if proposed not in ("keep", "move_duplicate", "move_organized", "ignore"):
            proposed = "ignore"
        status = row.get("status", "unreviewed")
        if status not in _REVIEW_STATUSES:
            status = "unreviewed"
        path = str(row.get("path") or record.relative_path)
        quality_for_file = quality_by_path.get(record.relative_path, [])
        members.append(
            {
                "rowId": row_id,
                "fileId": file_id,
                "name": record.name,
                "path": path,
                "sizeBytes": record.size_bytes,
                "status": status,
                "isKeeper": False,
                "proposedAction": proposed,
                "encoding": record.encoding_status or "Unknown",
                "integrity": member_integrity(record, quality_for_file),
            }
        )

    if not members:
        return {
            "status": "not_found",
            "groupId": gid,
            "members": [],
            "message": _NOT_FOUND_MESSAGE,
        }

    member_records = [
        files_by_id[member["fileId"]]
        for member in members
        if member["fileId"] in files_by_id
    ]
    keeper_file_id = pick_keeper_file_id(member_records) if member_records else members[0]["fileId"]
    for member in members:
        member["isKeeper"] = member["fileId"] == keeper_file_id

    members.sort(key=lambda member: (not member["isKeeper"], member["path"]))
    keeper_label = next(
        (member["name"] for member in members if member["fileId"] == keeper_file_id),
        members[0]["name"],
    )
    group_status = next(
        (row.get("status", "unreviewed") for row in group_rows if row.get("rowKind") == "group"),
        "unreviewed",
    )
    if group_status not in _REVIEW_STATUSES:
        group_status = "unreviewed"

    return {
        "status": "ok",
        "groupId": gid,
        "type": "relation",
        "groupStatus": group_status,
        "keeperFileId": keeper_file_id,
        "keeperLabel": keeper_label,
        "members": members,
        "evidence": {
            "matchKind": "relation_filename_v1",
            "relationKind": relation_group.relation_kind,
            "confidenceLabel": relation_group.confidence_label,
            "normalizedNames": list(relation_group.normalized_names),
            "matchedTokens": list(relation_group.matched_tokens),
            "differingTokens": list(relation_group.differing_tokens),
            "memberCount": len(members),
        },
    }
