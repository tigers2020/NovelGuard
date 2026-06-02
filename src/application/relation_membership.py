"""Build exact/near membership maps for relation detection (PR-20)."""

from __future__ import annotations

from domain.duplicate_exact import find_exact_duplicate_groups
from domain.duplicate_near import NearDuplicateGroup
from domain.models import FileRecord


def build_exact_membership_by_file_id(files: list[FileRecord]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for group in find_exact_duplicate_groups(files):
        for member_id in group.member_ids:
            mapping[member_id] = group.group_id
    return mapping


def build_near_membership_by_file_id(
    near_groups_by_id: dict[str, NearDuplicateGroup],
) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for group in near_groups_by_id.values():
        for member_id in group.member_file_ids:
            mapping[member_id] = group.group_id
    return mapping
