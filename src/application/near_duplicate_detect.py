"""Orchestrate near duplicate detection (PR-19)."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from application.near_text_reader import read_text_for_near_dup
from domain.duplicate_near import (
    NearDuplicateInput,
    NearDuplicateResult,
    find_near_duplicate_groups,
)
from domain.models import FileRecord


def build_exact_group_by_file_id(files: list[FileRecord]) -> dict[str, str]:
    from domain.duplicate_exact import find_exact_duplicate_groups

    mapping: dict[str, str] = {}
    for group in find_exact_duplicate_groups(files):
        for member_id in group.member_ids:
            mapping[member_id] = group.group_id
    return mapping


def run_near_duplicate_detection(
    *,
    root: Path,
    files: list[FileRecord],
    near_batch_id: str,
    exact_group_by_file_id: Mapping[str, str],
) -> NearDuplicateResult:
    inputs: list[NearDuplicateInput] = []
    for record in files:
        text = read_text_for_near_dup(root, record)
        inputs.append(
            NearDuplicateInput(
                file_id=record.id,
                path=record.relative_path,
                extension=record.extension,
                content_hash=record.content_sha256,
                size_bytes=record.size_bytes,
                mtime_ns=record.modified_at_ns,
                text=text,
            )
        )
    return find_near_duplicate_groups(
        inputs,
        exact_group_by_file_id=exact_group_by_file_id,
        near_batch_id=near_batch_id,
    )
