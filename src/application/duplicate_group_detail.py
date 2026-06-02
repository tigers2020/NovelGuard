"""Build DuplicateGroupDetail DTO from merged review cache (PR-18)."""

from __future__ import annotations

from typing import Any

from application.review_state_merge import _file_id_from_row_id
from domain.models import FileRecord

_REVIEW_STATUSES = frozenset({"unreviewed", "approved", "conflict", "excluded"})
_PROPOSED_ACTIONS = frozenset({"keep", "move_duplicate", "move_organized", "ignore"})
_NOT_FOUND_MESSAGE = "Group not found. Refresh the review list."


def index_quality_rows_by_path(
    quality_rows: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    by_path: dict[str, list[dict[str, Any]]] = {}
    for row in quality_rows:
        path = row.get("path")
        if isinstance(path, str) and path:
            by_path.setdefault(path, []).append(row)
    return by_path


def member_integrity(
    file_record: FileRecord,
    quality_rows_for_file: list[dict[str, Any]],
) -> dict[str, Any]:
    if not quality_rows_for_file:
        return {"status": "ok", "label": "OK", "issueCount": 0}
    severity_rank = {"error": 2, "warning": 1}
    best = max(
        quality_rows_for_file,
        key=lambda row: severity_rank.get(str(row.get("severity", "")), 0),
    )
    label = str(best.get("integrity") or best.get("issueType") or "issue")
    return {
        "status": "issue",
        "label": label,
        "issueCount": len(quality_rows_for_file),
    }


def build_duplicate_group_detail(
    group_id: str,
    *,
    review_rows: list[dict[str, Any]],
    files_by_id: dict[str, FileRecord],
    quality_by_path: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    gid = group_id.strip()
    group_rows = [r for r in review_rows if r.get("groupId") == gid]
    file_rows = [r for r in group_rows if r.get("rowKind") == "file"]
    header = next((r for r in group_rows if r.get("rowKind") == "group"), None)

    if not file_rows:
        return {
            "status": "not_found",
            "groupId": gid,
            "members": [],
            "message": _NOT_FOUND_MESSAGE,
        }

    members: list[dict[str, Any]] = []
    content_sha256 = ""

    for row in file_rows:
        row_id = str(row.get("id", ""))
        file_id = _file_id_from_row_id(row_id)
        if not file_id:
            continue
        record = files_by_id.get(file_id)
        if record is None:
            continue
        if record.content_sha256 and not content_sha256:
            content_sha256 = record.content_sha256

        path = str(row.get("path") or record.relative_path)
        quality_for_file = quality_by_path.get(record.relative_path, [])
        encoding = record.encoding_status or "Unknown"
        proposed = row.get("proposedAction", "move_duplicate")
        if proposed not in _PROPOSED_ACTIONS:
            proposed = "move_duplicate"

        members.append(
            {
                "rowId": row_id,
                "fileId": file_id,
                "name": str(row.get("name") or record.name),
                "path": path,
                "sizeBytes": int(row.get("sizeBytes") or record.size_bytes),
                "status": _coerce_status(row.get("status")),
                "isKeeper": proposed == "keep",
                "proposedAction": proposed,
                "targetFolder": row.get("targetFolder"),
                "encoding": encoding,
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

    members.sort(key=lambda m: (not m["isKeeper"], str(m["path"]).lower()))

    keeper = next((m for m in members if m["isKeeper"]), members[0])
    group_status = _coerce_status(header.get("status") if header else keeper["status"])

    return {
        "status": "ok",
        "groupId": gid,
        "type": "exact",
        "groupStatus": group_status,
        "keeperFileId": keeper["fileId"],
        "keeperLabel": keeper["name"],
        "members": members,
        "evidence": {
            "matchKind": "exact_content_hash",
            "contentSha256": content_sha256,
            "memberCount": len(members),
        },
        "movePlan": {
            "keeperAction": "keep",
            "duplicateAction": "move_duplicate",
            "targetFolder": "duplicate/",
        },
    }


def _coerce_status(value: Any) -> str:
    status = str(value) if value is not None else "unreviewed"
    return status if status in _REVIEW_STATUSES else "unreviewed"
