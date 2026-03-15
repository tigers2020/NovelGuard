"""관계 탐지 단계."""
from collections import defaultdict
from typing import Optional

from application.dto.duplicate_group_result import DuplicateGroupResult
from application.ports.log_sink import ILogSink
from application.use_cases.duplicate_detection.stages.base_stage import (
    PipelineContext,
    PipelineStage
)
from application.utils.debug_logger import debug_step
from domain.entities.file_entry import FileEntry
from domain.services.containment_detector import ContainmentDetector
from domain.value_objects.blocking_group import BlockingGroup
from domain.value_objects.filename_parse_result import FilenameParseResult


def _resolve_group_store_data(
    blocking_group: BlockingGroup,
    context: PipelineContext,
) -> Optional[tuple[list[int], dict[int, FileEntry], dict[int, FilenameParseResult]]]:
    """BlockingGroup을 FileDataStore file_id 및 엔트리/파싱 결과로 변환."""
    store_file_ids: list[int] = []
    group_file_entries: dict[int, FileEntry] = {}
    group_parse_results: dict[int, FilenameParseResult] = {}

    for original_id in blocking_group.file_ids:
        store_file_id = context.file_id_mapping.get(original_id)
        if store_file_id is None:
            continue
        store_file_ids.append(store_file_id)
        if store_file_id in context.file_entries_map:
            group_file_entries[store_file_id] = context.file_entries_map[store_file_id]
        if original_id in context.parse_results:
            group_parse_results[store_file_id] = context.parse_results[original_id]

    if len(store_file_ids) < 2:
        return None
    return (store_file_ids, group_file_entries, group_parse_results)


def _try_containment_pair(
    file_id_a: int,
    file_id_b: int,
    group_file_entries: dict[int, FileEntry],
    group_parse_results: dict[int, FilenameParseResult],
    context: PipelineContext,
    detector: ContainmentDetector,
) -> Optional[tuple[int, int]]:
    """한 쌍에 대해 containment를 탐지해 (container_store_id, contained_store_id) 또는 None 반환."""
    if file_id_a not in group_file_entries or file_id_a not in group_parse_results:
        return None
    if file_id_b not in group_file_entries or file_id_b not in group_parse_results:
        return None
    file_a = group_file_entries[file_id_a]
    parse_a = group_parse_results[file_id_a]
    file_b = group_file_entries[file_id_b]
    parse_b = group_parse_results[file_id_b]
    relation = detector.detect_containment(file_a, parse_a, file_b, parse_b)
    if not relation:
        return None
    container_store_id = context.file_id_mapping.get(relation.container_file_id)
    contained_store_id = context.file_id_mapping.get(relation.contained_file_id)
    if container_store_id is None or contained_store_id is None:
        return None
    return (container_store_id, contained_store_id)


def _compute_containment_relations(
    file_ids_list: list[int],
    group_file_entries: dict[int, FileEntry],
    group_parse_results: dict[int, FilenameParseResult],
    context: PipelineContext,
    detector: ContainmentDetector,
) -> dict[int, set[int]]:
    """쌍별 containment 관계를 탐지해 container_id -> {contained_ids} 맵으로 반환."""
    containment_relations: dict[int, set[int]] = defaultdict(set)
    for i, file_id_a in enumerate(file_ids_list):
        for j, file_id_b in enumerate(file_ids_list):
            if i >= j:
                continue
            pair = _try_containment_pair(
                file_id_a, file_id_b,
                group_file_entries, group_parse_results,
                context, detector,
            )
            if pair is not None:
                container_store_id, contained_store_id = pair
                containment_relations[container_store_id].add(contained_store_id)
    return containment_relations


def _emit_containment_groups(
    containment_relations: dict[int, set[int]],
    group_id: int,
) -> tuple[list[DuplicateGroupResult], int]:
    """Containment 맵을 DuplicateGroupResult 리스트로 변환하고 다음 group_id 반환."""
    results: list[DuplicateGroupResult] = []
    for container_store_id, contained_store_ids in containment_relations.items():
        if not contained_store_ids:
            continue
        group_id += 1
        containment_group = [container_store_id] + list(contained_store_ids)
        results.append(
            DuplicateGroupResult(
                group_id=group_id,
                duplicate_type="containment",
                file_ids=containment_group,
                recommended_keeper_id=container_store_id,
                evidence={"contained_count": len(contained_store_ids)},
                confidence=0.9,
            )
        )
    return (results, group_id)


def _is_containment_pair(
    file_id_a: int,
    file_id_b: int,
    containment_relations: dict[int, set[int]],
) -> bool:
    """두 file_id가 containment 쌍인지 여부."""
    contained_by_b = containment_relations.get(file_id_b)
    if contained_by_b and file_id_a in contained_by_b:
        return True
    contained_by_a = containment_relations.get(file_id_a)
    return bool(contained_by_a and file_id_b in contained_by_a)


def _try_version_result(
    file_id_a: int,
    file_id_b: int,
    group_file_entries: dict[int, FileEntry],
    group_parse_results: dict[int, FilenameParseResult],
    containment_relations: dict[int, set[int]],
    context: PipelineContext,
    group_id: int,
    detector: ContainmentDetector,
) -> Optional[tuple[DuplicateGroupResult, int]]:
    """한 쌍에 대해 version 관계를 탐지해 (DuplicateGroupResult, next_group_id) 또는 None 반환."""
    if file_id_a not in group_file_entries or file_id_a not in group_parse_results:
        return None
    if file_id_b not in group_file_entries or file_id_b not in group_parse_results:
        return None
    if _is_containment_pair(file_id_a, file_id_b, containment_relations):
        return None
    file_a = group_file_entries[file_id_a]
    parse_a = group_parse_results[file_id_a]
    file_b = group_file_entries[file_id_b]
    parse_b = group_parse_results[file_id_b]
    version_relation = detector.detect_version(file_a, parse_a, file_b, parse_b)
    if not version_relation:
        return None
    newer_store_id = context.file_id_mapping.get(version_relation.newer_file_id)
    older_store_id = context.file_id_mapping.get(version_relation.older_file_id)
    if newer_store_id is None or older_store_id is None:
        return None
    group_id += 1
    version_group = [newer_store_id, older_store_id]
    result = DuplicateGroupResult(
        group_id=group_id,
        duplicate_type="version",
        file_ids=version_group,
        recommended_keeper_id=newer_store_id,
        evidence=version_relation.evidence,
        confidence=version_relation.confidence,
    )
    return (result, group_id)


def _compute_version_groups(
    file_ids_list: list[int],
    group_file_entries: dict[int, FileEntry],
    group_parse_results: dict[int, FilenameParseResult],
    containment_relations: dict[int, set[int]],
    context: PipelineContext,
    group_id: int,
    detector: ContainmentDetector,
) -> tuple[list[DuplicateGroupResult], int]:
    """Version 관계를 탐지해 DuplicateGroupResult 리스트와 다음 group_id 반환."""
    results: list[DuplicateGroupResult] = []
    for i, file_id_a in enumerate(file_ids_list):
        for j, file_id_b in enumerate(file_ids_list):
            if i >= j:
                continue
            one = _try_version_result(
                file_id_a, file_id_b,
                group_file_entries, group_parse_results,
                containment_relations, context, group_id, detector,
            )
            if one is not None:
                result, group_id = one
                results.append(result)
    return (results, group_id)


class RelationDetectionStage(PipelineStage):
    """관계 탐지 단계.

    각 BlockingGroup 내에서 containment/version 관계를 탐지합니다.
    """

    def __init__(
        self,
        containment_detector: ContainmentDetector,
        log_sink: Optional[ILogSink] = None
    ) -> None:
        """관계 탐지 단계 초기화.

        Args:
            containment_detector: 포함/버전 관계 탐지기.
            log_sink: 로그 싱크 (선택적).
        """
        self._containment_detector = containment_detector
        self._log_sink = log_sink

    @property
    def name(self) -> str:
        return "관계 탐지"

    def execute(self, context: PipelineContext) -> PipelineContext:
        """관계 탐지 단계 실행.

        Args:
            context: 파이프라인 컨텍스트.

        Returns:
            업데이트된 컨텍스트.
        """
        debug_step(
            self._log_sink,
            "duplicate_detection_stage",
            {"stage": self.name}
        )

        if len(context.blocking_groups) == 0:
            context.results = []
            return context

        group_results: list[DuplicateGroupResult] = []
        group_id = 0
        containment_relations: dict[int, set[int]] = {}

        for blocking_group in context.blocking_groups:
            resolved = _resolve_group_store_data(blocking_group, context)
            if resolved is None:
                continue
            store_file_ids, group_file_entries, group_parse_results = resolved

            if context.request.enable_containment:
                containment_relations = _compute_containment_relations(
                    store_file_ids,
                    group_file_entries,
                    group_parse_results,
                    context,
                    self._containment_detector,
                )
                containment_results, group_id = _emit_containment_groups(
                    containment_relations, group_id
                )
                group_results.extend(containment_results)

            if context.request.enable_version:
                version_results, group_id = _compute_version_groups(
                    store_file_ids,
                    group_file_entries,
                    group_parse_results,
                    containment_relations,
                    context,
                    group_id,
                    self._containment_detector,
                )
                group_results.extend(version_results)

        context.results = group_results
        return context
