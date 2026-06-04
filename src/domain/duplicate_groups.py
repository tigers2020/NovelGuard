"""Aggregate exact and head/tail variant duplicate groups."""

from __future__ import annotations

from pathlib import Path

from domain.duplicate_content_variant import find_head_tail_variant_groups
from domain.duplicate_exact import find_exact_duplicate_groups
from domain.models import DuplicateGroup, FileRecord


def find_duplicate_groups(
    files: list[FileRecord],
    *,
    library_root: Path | None = None,
) -> list[DuplicateGroup]:
    exact = find_exact_duplicate_groups(files)
    exact_member_sets = {frozenset(group.member_ids) for group in exact}
    variant: list[DuplicateGroup] = []
    if library_root is not None:
        variant = find_head_tail_variant_groups(
            library_root,
            files,
            byte_identical_member_sets=exact_member_sets,
        )
    return [*exact, *variant]
