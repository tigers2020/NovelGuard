"""Head/tail variant groups for large novels that differ slightly in the middle."""

from __future__ import annotations

import hashlib
from collections import defaultdict
from pathlib import Path

from domain.models import DuplicateGroup, FileRecord
from infrastructure.large_file_sampling import (
    SAMPLE_BYTES,
    is_large_file,
    read_head_tail,
)

HEAD_TAIL_VARIANT_GROUP_PREFIX = "dup-ht-"
HEAD_TAIL_VARIANT_SIZE_RATIO_MIN = 0.995


def is_head_tail_variant_group_id(group_id: str) -> bool:
    return group_id.startswith(HEAD_TAIL_VARIANT_GROUP_PREFIX)


def head_tail_sample_hash(path: Path, size_bytes: int) -> str | None:
    """SHA-256 of head+tail samples (size excluded) for variant bucketing."""
    if size_bytes <= 0:
        return None
    try:
        head, tail = read_head_tail(path, size_bytes, SAMPLE_BYTES)
    except OSError:
        return None
    digest = hashlib.sha256()
    digest.update(head)
    digest.update(tail)
    return digest.hexdigest()


def _size_ratio_ok(left: int, right: int) -> bool:
    if left <= 0 or right <= 0:
        return False
    return min(left, right) / max(left, right) >= HEAD_TAIL_VARIANT_SIZE_RATIO_MIN


def _pick_keeper(members: list[FileRecord]) -> FileRecord:
    from domain.keeper_selection import pick_keeper_record

    return pick_keeper_record(members)


def find_head_tail_variant_groups(
    library_root: Path,
    files: list[FileRecord],
    *,
    byte_identical_member_sets: set[frozenset[str]] | None = None,
) -> list[DuplicateGroup]:
    """Group large files with matching head/tail samples and similar size."""
    suppressed = byte_identical_member_sets or set()
    by_sample: dict[str, list[FileRecord]] = defaultdict(list)

    for record in files:
        if not is_large_file(record.size_bytes):
            continue
        path = library_root / record.relative_path
        sample_hash = head_tail_sample_hash(path, record.size_bytes)
        if sample_hash is None:
            continue
        by_sample[sample_hash].append(record)

    groups: list[DuplicateGroup] = []
    for sample_hash, bucket in by_sample.items():
        if len(bucket) < 2:
            continue
        cluster = _cluster_by_size_ratio(bucket)
        for members in cluster:
            if len(members) < 2:
                continue
            member_ids = tuple(sorted(record.id for record in members))
            if frozenset(member_ids) in suppressed:
                continue
            keeper = _pick_keeper(members)
            group_id = f"{HEAD_TAIL_VARIANT_GROUP_PREFIX}{sample_hash[:16]}"
            groups.append(
                DuplicateGroup(
                    group_id=group_id,
                    member_ids=member_ids,
                    keeper_id=keeper.id,
                )
            )
    return groups


def _cluster_by_size_ratio(members: list[FileRecord]) -> list[list[FileRecord]]:
    """Greedy clusters: each file joins a cluster if size-compatible with all members."""
    sorted_members = sorted(members, key=lambda record: record.size_bytes)
    clusters: list[list[FileRecord]] = []
    for record in sorted_members:
        placed = False
        for cluster in clusters:
            if all(_size_ratio_ok(record.size_bytes, other.size_bytes) for other in cluster):
                cluster.append(record)
                placed = True
                break
        if not placed:
            clusters.append([record])
    return [cluster for cluster in clusters if len(cluster) >= 2]
