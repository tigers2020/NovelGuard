"""Exact 중복 탐지 서비스."""

from domain.entities.file_entry import FileEntry
from domain.ports.content_hash import IHashService
from domain.value_objects.blocking_group import BlockingGroup
from domain.value_objects.duplicate_relation import ExactDuplicateRelation


class ExactDuplicateDetector:
    """Exact 중복 탐지 서비스.

    내용이 100% 동일한 파일을 탐지하는 서비스.
    해시 기반으로 동일성을 판정.
    """

    def __init__(self, hash_service: IHashService) -> None:
        """ExactDuplicateDetector 초기화.

        Args:
            hash_service: 해시 서비스 (Port).
        """
        self._hash_service = hash_service

    def detect_exact(
        self, blocking_group: BlockingGroup, file_entries: dict[int, FileEntry]
    ) -> list[ExactDuplicateRelation]:
        """Exact 중복 탐지.

        Args:
            blocking_group: Blocking Group.
            file_entries: 파일 ID -> FileEntry 매핑.

        Returns:
            ExactDuplicateRelation 리스트.
        """
        size_groups = self._build_size_groups(blocking_group, file_entries)
        exact_relations: list[ExactDuplicateRelation] = []
        for size, file_ids in size_groups.items():
            exact_relations.extend(self._relations_for_size_group(size, file_ids, file_entries))
        return exact_relations

    def _build_size_groups(
        self, blocking_group: BlockingGroup, file_entries: dict[int, FileEntry]
    ) -> dict[int, list[int]]:
        """같은 크기끼리 파일 ID를 묶는다."""
        size_groups: dict[int, list[int]] = {}
        for file_id in blocking_group.file_ids:
            if file_id not in file_entries:
                continue
            file_entry = file_entries[file_id]
            size_groups.setdefault(file_entry.size, []).append(file_id)
        return size_groups

    def _relations_for_size_group(
        self, size: int, file_ids: list[int], file_entries: dict[int, FileEntry]
    ) -> list[ExactDuplicateRelation]:
        if len(file_ids) < 2:
            return []
        out: list[ExactDuplicateRelation] = []
        prefix_hash_groups = self._group_by_prefix_hash(file_ids, file_entries)
        for prefix_hash, prefix_file_ids in prefix_hash_groups.items():
            if len(prefix_file_ids) < 2:
                continue
            out.extend(
                self._relations_for_prefix_group(size, prefix_hash, prefix_file_ids, file_entries)
            )
        return out

    def _relations_for_prefix_group(
        self,
        size: int,
        prefix_hash: str,
        prefix_file_ids: list[int],
        file_entries: dict[int, FileEntry],
    ) -> list[ExactDuplicateRelation]:
        out: list[ExactDuplicateRelation] = []
        suffix_hash_groups = self._group_by_suffix_hash(prefix_file_ids, file_entries)
        for suffix_hash, suffix_file_ids in suffix_hash_groups.items():
            if len(suffix_file_ids) < 2:
                continue
            out.extend(
                self._relations_for_suffix_group(
                    size, prefix_hash, suffix_hash, suffix_file_ids, file_entries
                )
            )
        return out

    def _relations_for_suffix_group(
        self,
        size: int,
        prefix_hash: str,
        suffix_hash: str,
        suffix_file_ids: list[int],
        file_entries: dict[int, FileEntry],
    ) -> list[ExactDuplicateRelation]:
        out: list[ExactDuplicateRelation] = []
        full_hash_groups = self._group_by_full_hash(suffix_file_ids, file_entries)
        for full_hash, hash_file_ids in full_hash_groups.items():
            if len(hash_file_ids) < 2:
                continue
            out.append(
                self._make_exact_relation(size, prefix_hash, suffix_hash, full_hash, hash_file_ids)
            )
        return out

    @staticmethod
    def _make_exact_relation(
        size: int,
        prefix_hash: str,
        suffix_hash: str,
        full_hash: str,
        hash_file_ids: list[int],
    ) -> ExactDuplicateRelation:
        evidence = {
            "hash": full_hash,
            "size": size,
            "prefix_hash": prefix_hash,
            "suffix_hash": suffix_hash,
        }
        return ExactDuplicateRelation(
            file_ids=hash_file_ids,
            evidence=evidence,
            confidence=1.0,
        )

    def _group_by_prefix_hash(
        self, file_ids: list[int], file_entries: dict[int, FileEntry]
    ) -> dict[str, list[int]]:
        """Prefix hash로 그룹화."""
        groups: dict[str, list[int]] = {}

        for file_id in file_ids:
            file_entry = file_entries[file_id]
            prefix_hash = self._hash_service.calculate_prefix_hash(file_entry.path)

            if prefix_hash not in groups:
                groups[prefix_hash] = []
            groups[prefix_hash].append(file_id)

        return groups

    def _group_by_suffix_hash(
        self, file_ids: list[int], file_entries: dict[int, FileEntry]
    ) -> dict[str, list[int]]:
        """Suffix hash로 그룹화."""
        groups: dict[str, list[int]] = {}

        for file_id in file_ids:
            file_entry = file_entries[file_id]
            suffix_hash = self._hash_service.calculate_suffix_hash(file_entry.path)

            if suffix_hash not in groups:
                groups[suffix_hash] = []
            groups[suffix_hash].append(file_id)

        return groups

    def _group_by_full_hash(
        self, file_ids: list[int], file_entries: dict[int, FileEntry]
    ) -> dict[str, list[int]]:
        """Full hash로 그룹화."""
        groups: dict[str, list[int]] = {}

        for file_id in file_ids:
            file_entry = file_entries[file_id]
            full_hash = self._hash_service.calculate_hash(file_entry.path)

            if full_hash not in groups:
                groups[full_hash] = []
            groups[full_hash].append(file_id)

        return groups
