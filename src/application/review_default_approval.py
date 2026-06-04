"""Seed default review state after scan (keeper + auto-approve all duplicate types)."""

from __future__ import annotations

from application.ports.library_index import LibraryIndexPort
from domain.keeper_selection import pick_keeper_record
from domain.models import DuplicateGroup, FileRecord


def _member_records(
    member_ids: tuple[str, ...] | list[str],
    files_by_id: dict[str, FileRecord],
) -> list[FileRecord]:
    return [files_by_id[mid] for mid in member_ids if mid in files_by_id]


def _seed_group(
    index: LibraryIndexPort,
    folder_path: str,
    group_id: str,
    members: list[FileRecord],
    stored_groups: dict,
) -> bool:
    if len(members) < 2:
        return False
    keeper = pick_keeper_record(members)
    entry = stored_groups.get(group_id)
    keeper_override = entry[0] if entry else None
    group_status = entry[1] if entry else None
    if keeper_override is not None and group_status is not None:
        return False
    index.upsert_review_group(
        folder_path,
        group_id,
        keeper_file_id=keeper.id if keeper_override is None else None,
        group_status="approved" if group_status is None else None,
    )
    return True


def seed_default_exact_group_approvals(
    index: LibraryIndexPort,
    folder_path: str,
    groups: list[DuplicateGroup],
    files_by_id: dict[str, FileRecord],
) -> int:
    stored = index.load_review_state(folder_path)
    seeded = 0
    for group in groups:
        if _seed_group(
            index,
            folder_path,
            group.group_id,
            _member_records(group.member_ids, files_by_id),
            stored.groups,
        ):
            seeded += 1
    return seeded


def seed_default_near_relation_approvals(
    index: LibraryIndexPort,
    folder_path: str,
    member_ids_by_group: dict[str, list[str]],
    files_by_id: dict[str, FileRecord],
) -> int:
    stored = index.load_review_state(folder_path)
    seeded = 0
    for group_id, member_ids in member_ids_by_group.items():
        if _seed_group(
            index,
            folder_path,
            group_id,
            _member_records(member_ids, files_by_id),
            stored.groups,
        ):
            seeded += 1
    return seeded
