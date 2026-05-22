"""Exact 중복 탐지 서비스."""

from collections import defaultdict
from dataclasses import dataclass

from domain.entities.file_entry import FileEntry
from domain.ports.content_hash import IHashService
from domain.ports.staged_content_fingerprints import StagedContentFingerprints
from domain.value_objects.blocking_group import BlockingGroup
from domain.value_objects.detection_config import DetectionDefaults
from domain.value_objects.duplicate_relation import ExactDuplicateRelation
from domain.value_objects.exact_detect_metrics import ExactDetectMetrics
from domain.value_objects.exact_detection_result import ExactDetectionResult


@dataclass
class _MetricsAccumulator:
    """Mutable counters for one detect_exact invocation."""

    size_bucket_count: int = 1
    files_considered: int = 0
    prefix_hash_count: int = 0
    suffix_hash_count: int = 0
    full_hash_count: int = 0
    file_open_count: int = 0

    def freeze(self) -> ExactDetectMetrics:
        return ExactDetectMetrics(
            size_bucket_count=self.size_bucket_count,
            files_considered=self.files_considered,
            prefix_hash_count=self.prefix_hash_count,
            suffix_hash_count=self.suffix_hash_count,
            full_hash_count=self.full_hash_count,
            file_open_count=self.file_open_count,
        )


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
    ) -> ExactDetectionResult:
        """Exact 중복 탐지.

        Args:
            blocking_group: Blocking Group (one size bucket from the stage).
            file_entries: 파일 ID -> FileEntry 매핑.

        Returns:
            Relations and instrumentation metrics (metrics do not affect grouping).
        """
        metrics = _MetricsAccumulator()
        metrics.files_considered = sum(1 for fid in blocking_group.file_ids if fid in file_entries)
        size_groups = self._build_size_groups(blocking_group, file_entries)
        exact_relations: list[ExactDuplicateRelation] = []
        for size, file_ids in size_groups.items():
            exact_relations.extend(
                self._relations_for_size_group(size, file_ids, file_entries, metrics)
            )
        return ExactDetectionResult(relations=exact_relations, metrics=metrics.freeze())

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

    def _read_staged(
        self,
        file_entry: FileEntry,
        metrics: _MetricsAccumulator,
        *,
        need_full: bool,
    ) -> StagedContentFingerprints:
        metrics.file_open_count += 1
        metrics.prefix_hash_count += 1
        metrics.suffix_hash_count += 1
        if need_full:
            metrics.full_hash_count += 1
        return self._hash_service.read_staged_fingerprints(
            file_entry.path, file_entry.size, need_full=need_full
        )

    def _relations_for_size_group(
        self,
        size: int,
        file_ids: list[int],
        file_entries: dict[int, FileEntry],
        metrics: _MetricsAccumulator,
    ) -> list[ExactDuplicateRelation]:
        if len(file_ids) < 2:
            return []
        out: list[ExactDuplicateRelation] = []

        # P2-1: prefix sample covers entire file when size <= SAMPLE_SIZE (same size bucket only).
        if size <= DetectionDefaults.SAMPLE_SIZE:
            prefix_groups: dict[str, list[int]] = {}
            for file_id in file_ids:
                staged = self._read_staged(file_entries[file_id], metrics, need_full=False)
                prefix_groups.setdefault(staged.prefix_hash, []).append(file_id)
            for prefix_hash, prefix_file_ids in prefix_groups.items():
                if len(prefix_file_ids) < 2:
                    continue
                out.append(
                    self._make_exact_relation(
                        size,
                        prefix_hash,
                        prefix_hash,
                        prefix_hash,
                        prefix_file_ids,
                    )
                )
            return out

        staged_by_id: dict[int, StagedContentFingerprints] = {}
        for file_id in file_ids:
            staged_by_id[file_id] = self._read_staged(
                file_entries[file_id], metrics, need_full=False
            )

        large_prefix_groups: dict[str, list[int]] = defaultdict(list)
        for file_id, staged in staged_by_id.items():
            large_prefix_groups[staged.prefix_hash].append(file_id)

        for prefix_hash, prefix_file_ids in large_prefix_groups.items():
            if len(prefix_file_ids) < 2:
                continue
            suffix_groups: dict[str, list[int]] = defaultdict(list)
            for file_id in prefix_file_ids:
                suffix_groups[staged_by_id[file_id].suffix_hash].append(file_id)
            for suffix_hash, suffix_file_ids in suffix_groups.items():
                if len(suffix_file_ids) < 2:
                    continue
                full_groups: dict[str, list[int]] = defaultdict(list)
                for file_id in suffix_file_ids:
                    staged_full = self._read_staged(file_entries[file_id], metrics, need_full=True)
                    full_hash = staged_full.full_hash
                    if full_hash is None:
                        continue
                    full_groups[full_hash].append(file_id)
                for full_hash, hash_file_ids in full_groups.items():
                    if len(hash_file_ids) < 2:
                        continue
                    out.append(
                        self._make_exact_relation(
                            size,
                            prefix_hash,
                            suffix_hash,
                            full_hash,
                            hash_file_ids,
                        )
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
