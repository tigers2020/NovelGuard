"""관계 탐지 단계."""
from collections import defaultdict
from typing import Optional

from application.dto.duplicate_group_result import DuplicateGroupResult
from application.ports.log_sink import ILogSink
from application.use_cases.duplicate_detection.stages.base_stage import (
    PipelineContext,
    PipelineStage,
)
from application.utils.debug_logger import debug_step
from domain.entities.file_entry import FileEntry
from domain.services.containment_detector import ContainmentDetector
from domain.value_objects.blocking_group import BlockingGroup
from domain.value_objects.filename_parse_result import FilenameParseResult

# 범위가 없는 항목 정렬 시 맨 뒤로 보내기 위한 sentinel
_NO_RANGE_ORDER = (float("inf"), float("inf"))


def _range_key_for_sort(
    file_id: int,
    group_parse_results: dict[int, FilenameParseResult],
) -> tuple[float, float]:
    """파일의 (range_start, range_end)를 정렬 키로 반환. 범위 없으면 _NO_RANGE_ORDER."""
    parse = group_parse_results.get(file_id)
    if not parse:
        return _NO_RANGE_ORDER
    if parse.has_segments and parse.primary_segment is not None:
        seg = parse.primary_segment
        return (float(seg.start), float(seg.end))
    if parse.has_range and parse.range_start is not None and parse.range_end is not None:
        return (float(parse.range_start), float(parse.range_end))
    return _NO_RANGE_ORDER


def _range_start_for_grouping(
    file_id: int,
    group_parse_results: dict[int, FilenameParseResult],
) -> Optional[int]:
    """Version 서브그룹용 range_start. 없으면 None."""
    parse = group_parse_results.get(file_id)
    if not parse:
        return None
    if parse.has_segments and parse.primary_segment is not None:
        return parse.primary_segment.start
    return parse.range_start


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


def _sorted_files_with_ranges(
    file_ids_list: list[int],
    group_parse_results: dict[int, FilenameParseResult],
) -> list[tuple[int, float, float]]:
    """범위가 있는 파일만 (file_id, start, end)로 모아 (start, end) 기준 정렬."""
    rows: list[tuple[int, float, float]] = []
    for fid in file_ids_list:
        key = _range_key_for_sort(fid, group_parse_results)
        if key == _NO_RANGE_ORDER:
            continue
        start_f, end_f = key
        rows.append((fid, start_f, end_f))
    rows.sort(key=lambda r: (r[1], r[2]))
    return rows


def _process_containment_pair_candidate(
    file_id_a: int,
    start_a: float,
    end_a: float,
    file_id_b: int,
    start_b: float,
    end_b: float,
    group_file_entries: dict[int, FileEntry],
    group_parse_results: dict[int, FilenameParseResult],
    context: PipelineContext,
    detector: ContainmentDetector,
    containment_relations: dict[int, set[int]],
) -> bool:
    """한 inner-loop 쌍을 처리. True면 정렬 순서상 더 이상 후보 없음(inner break)."""
    if start_b > end_a:
        return True
    if (start_a, end_a) == (start_b, end_b):
        return False
    if not (end_a >= end_b or end_b >= end_a):
        return False
    pair = _try_containment_pair(
        file_id_a,
        file_id_b,
        group_file_entries,
        group_parse_results,
        context,
        detector,
    )
    if pair is not None:
        container_store_id, contained_store_id = pair
        containment_relations[container_store_id].add(contained_store_id)
    return False


def _compute_containment_relations(
    file_ids_list: list[int],
    group_file_entries: dict[int, FileEntry],
    group_parse_results: dict[int, FilenameParseResult],
    context: PipelineContext,
    detector: ContainmentDetector,
) -> dict[int, set[int]]:
    """쌍별 containment 관계를 탐지해 container_id -> {contained_ids} 맵으로 반환.

    범위 정렬 후, 한 구간이 다른 구간을 포함할 수 있는 후보 쌍만 비교하여 O(n²) 호출을 줄인다.
    """
    containment_relations: dict[int, set[int]] = defaultdict(set)
    rows = _sorted_files_with_ranges(file_ids_list, group_parse_results)
    n = len(rows)
    for i in range(n):
        file_id_a, start_a, end_a = rows[i]
        for j in range(i + 1, n):
            file_id_b, start_b, end_b = rows[j]
            if _process_containment_pair_candidate(
                file_id_a,
                start_a,
                end_a,
                file_id_b,
                start_b,
                end_b,
                group_file_entries,
                group_parse_results,
                context,
                detector,
                containment_relations,
            ):
                break
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


def _collect_version_results_for_ids(
    ids: list[int],
    group_file_entries: dict[int, FileEntry],
    group_parse_results: dict[int, FilenameParseResult],
    containment_relations: dict[int, set[int]],
    context: PipelineContext,
    group_id: int,
    detector: ContainmentDetector,
) -> tuple[list[DuplicateGroupResult], int]:
    """동일 range_start 버킷 내 모든 순서 있는 쌍에 대해 version 그룹을 수집."""
    results: list[DuplicateGroupResult] = []
    for i, file_id_a in enumerate(ids):
        for j, file_id_b in enumerate(ids):
            if i >= j:
                continue
            one = _try_version_result(
                file_id_a,
                file_id_b,
                group_file_entries,
                group_parse_results,
                containment_relations,
                context,
                group_id,
                detector,
            )
            if one is not None:
                result, group_id = one
                results.append(result)
    return (results, group_id)


def _compute_version_groups(
    file_ids_list: list[int],
    group_file_entries: dict[int, FileEntry],
    group_parse_results: dict[int, FilenameParseResult],
    containment_relations: dict[int, set[int]],
    context: PipelineContext,
    group_id: int,
    detector: ContainmentDetector,
) -> tuple[list[DuplicateGroupResult], int]:
    """Version 관계를 탐지해 DuplicateGroupResult 리스트와 다음 group_id 반환.

    range_start가 같은 파일끼리만 쌍 비교 (detect_version 조건과 일치, 비교 횟수 감소).
    """
    results: list[DuplicateGroupResult] = []
    by_range_start: dict[Optional[int], list[int]] = defaultdict(list)
    for file_id in file_ids_list:
        rs = _range_start_for_grouping(file_id, group_parse_results)
        by_range_start[rs].append(file_id)
    for _range_start, ids in by_range_start.items():
        if len(ids) < 2:
            continue
        bucket_results, group_id = _collect_version_results_for_ids(
            ids,
            group_file_entries,
            group_parse_results,
            containment_relations,
            context,
            group_id,
            detector,
        )
        results.extend(bucket_results)
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
