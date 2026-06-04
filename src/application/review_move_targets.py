"""Shared rules for which review file rows are executable move targets."""

from __future__ import annotations

from typing import Any

_MOVEABLE_TYPES = frozenset({"exact", "near", "relation"})
_TYPE_RANK = {"exact": 0, "near": 1, "relation": 2, "move_only": 3}


def is_approved_non_keeper_file_row(row: dict[str, Any]) -> bool:
    """Approved duplicate member file that should move (not the keeper)."""
    if row.get("rowKind") != "file":
        return False
    if row.get("type") not in _MOVEABLE_TYPES:
        return False
    if row.get("status") != "approved":
        return False
    return row.get("proposedAction") != "keep"


def normalize_row_for_move_execution(row: dict[str, Any]) -> dict[str, Any]:
    """Map legacy ``ignore`` + approved rows to ``move_duplicate`` for preview/apply."""
    updated = dict(row)
    if not is_approved_non_keeper_file_row(updated):
        return updated
    if updated.get("proposedAction") == "ignore":
        updated["proposedAction"] = "move_duplicate"
    if updated.get("proposedAction") == "move_duplicate":
        updated["targetFolder"] = updated.get("targetFolder") or "duplicate/"
    return updated


def reconcile_approved_duplicate_proposed_actions(
    rows: list[dict[str, Any]],
    files_by_id: dict[str, Any],
    *,
    stored_groups: dict[str, tuple[str | None, str | None]] | None = None,
) -> None:
    """Re-derive keeper vs move for approved groups (fixes stale all-keep caches)."""
    from application.review_state_merge import _file_id_from_row_id
    from domain.keeper_selection import pick_keeper_record
    from domain.models import FileRecord

    if not files_by_id:
        return

    typed_files: dict[str, FileRecord] = files_by_id  # type: ignore[assignment]
    by_group: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        if row.get("rowKind") != "file":
            continue
        if row.get("type") not in _MOVEABLE_TYPES:
            continue
        group_id = row.get("groupId")
        if isinstance(group_id, str):
            by_group.setdefault(group_id, []).append(row)

    for group_id, member_rows in by_group.items():
        approved_rows = [row for row in member_rows if row.get("status") == "approved"]
        if len(approved_rows) < 2:
            continue
        records: list[FileRecord] = []
        for row in member_rows:
            file_id = _file_id_from_row_id(str(row.get("id", "")))
            if file_id and file_id in typed_files:
                records.append(typed_files[file_id])
        if len(records) < 2:
            continue

        keeper_id: str | None = None
        if stored_groups is not None:
            entry = stored_groups.get(group_id)
            if entry:
                override = entry[0]
                if override and override in typed_files:
                    keeper_id = override
        if keeper_id is None:
            keeper_id = pick_keeper_record(records).id
        keeper_name = typed_files[keeper_id].name

        for row in member_rows:
            if row.get("status") != "approved":
                continue
            file_id = _file_id_from_row_id(str(row.get("id", "")))
            is_keeper = file_id == keeper_id
            row["keeperLabel"] = keeper_name
            row["proposedAction"] = "keep" if is_keeper else "move_duplicate"
            row["targetFolder"] = None if is_keeper else "duplicate/"


def _type_rank(row: dict[str, Any]) -> int:
    return _TYPE_RANK.get(str(row.get("type", "")), 99)


def collect_canonical_approved_move_target_rows(
    rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """One executable move row per file; exact group decision beats near/relation."""
    from application.review_state_merge import _file_id_from_row_id

    approved_by_file: dict[str, tuple[int, str, dict[str, Any]]] = {}
    for row in rows:
        if row.get("rowKind") != "file":
            continue
        if row.get("type") not in _MOVEABLE_TYPES:
            continue
        if row.get("status") != "approved":
            continue
        file_id = _file_id_from_row_id(str(row.get("id", "")))
        if not file_id:
            continue
        normalized = normalize_row_for_move_execution(dict(row))
        rank = _type_rank(normalized)
        group_id = str(normalized.get("groupId", ""))
        current = approved_by_file.get(file_id)
        if current is None or rank < current[0] or (rank == current[0] and group_id < current[1]):
            approved_by_file[file_id] = (rank, group_id, normalized)

    move_targets: list[dict[str, Any]] = []
    for _rank, _group_id, row in approved_by_file.values():
        if is_approved_non_keeper_file_row(row):
            move_targets.append(row)

    return sorted(
        move_targets,
        key=lambda row: (_type_rank(row), str(row.get("groupId", "")), str(row.get("id", ""))),
    )


def count_approved_move_targets(rows: list[dict[str, Any]]) -> tuple[int, int]:
    """Return (duplicate_member_file_count, approved_move_target_count)."""
    file_count = 0
    for row in rows:
        if row.get("rowKind") != "file" or row.get("type") not in _MOVEABLE_TYPES:
            continue
        file_count += 1
    move_targets = len(collect_canonical_approved_move_target_rows(rows))
    return file_count, move_targets
