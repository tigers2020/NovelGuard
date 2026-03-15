"""Near(유사) 중복 탐지 단계."""
from typing import Optional

from application.dto.duplicate_group_result import DuplicateGroupResult
from application.ports.log_sink import ILogSink
from application.use_cases.duplicate_detection.stages.base_stage import (
    PipelineContext,
    PipelineStage
)
from application.utils.debug_logger import debug_step
from domain.entities.file_entry import FileEntry
from domain.services.near_duplicate_detector import NearDuplicateDetector
from domain.value_objects.blocking_group import BlockingGroup
from domain.value_objects.filename_parse_result import FilenameParseResult


def _build_parse_by_store(context: PipelineContext) -> dict[int, FilenameParseResult]:
    """parse_results를 store file_id 기준으로 매핑."""
    result: dict[int, FilenameParseResult] = {}
    for orig_id, parse_result in context.parse_results.items():
        store_id = context.file_id_mapping.get(orig_id)
        if store_id is not None:
            result[store_id] = parse_result
    return result


def _store_ids_for_group(
    blocking_group: BlockingGroup,
    context: PipelineContext
) -> list[int]:
    """Blocking 그룹의 file_ids 중 store에 존재하는 ID만 반환."""
    store_ids = []
    for orig_id in blocking_group.file_ids:
        store_id = context.file_id_mapping.get(orig_id)
        if store_id is not None and store_id in context.file_entries_map:
            store_ids.append(store_id)
    return store_ids


def _pick_keeper(file_ids: list[int], file_entries_map: dict[int, FileEntry]) -> int:
    """수정일이 가장 최신인 파일 ID 반환."""
    best_id = file_ids[0]
    best_mtime = None
    for fid in file_ids:
        entry = file_entries_map.get(fid)
        if entry and (best_mtime is None or entry.mtime > best_mtime):
            best_mtime = entry.mtime
            best_id = fid
    return best_id


class NearDuplicateStage(PipelineStage):
    """Near 중복 탐지 단계.

    Blocking 그룹 내에서 SimHash 유사도 기반 유사 중복을 탐지합니다.
    enable_near가 True이고 NearDuplicateDetector(SimHash 서비스)가 주입된 경우에만 동작.
    """

    def __init__(
        self,
        near_detector: Optional[NearDuplicateDetector] = None,
        log_sink: Optional[ILogSink] = None
    ) -> None:
        """Near 중복 단계 초기화.

        Args:
            near_detector: Near 중복 탐지기 (None이면 no-op).
            log_sink: 로그 싱크 (선택적).
        """
        self._near_detector = near_detector
        self._log_sink = log_sink

    @property
    def name(self) -> str:
        return "Near 중복 탐지"

    def _process_blocking_group(
        self,
        blocking_group: BlockingGroup,
        context: PipelineContext,
        parse_by_store: dict[int, FilenameParseResult],
        next_group_id: int
    ) -> tuple[list[DuplicateGroupResult], int]:
        """단일 blocking 그룹에 대해 near 탐지 후 결과 목록과 다음 group_id 반환."""
        assert self._near_detector is not None  # 호출 전 execute에서 이미 검사됨
        store_ids = _store_ids_for_group(blocking_group, context)
        if len(store_ids) < 2:
            return [], next_group_id

        synthetic_group = BlockingGroup(
            series_title_norm=blocking_group.series_title_norm,
            extension=blocking_group.extension,
            file_ids=store_ids,
            range_start=blocking_group.range_start
        )
        relations = self._near_detector.detect_near(
            synthetic_group,
            context.file_entries_map,
            parse_by_store
        )
        results = []
        for rel in relations:
            keeper_id = _pick_keeper(rel.file_ids, context.file_entries_map)
            results.append(
                DuplicateGroupResult(
                    group_id=next_group_id,
                    duplicate_type="near",
                    file_ids=list(rel.file_ids),
                    recommended_keeper_id=keeper_id,
                    evidence=dict(rel.evidence),
                    confidence=rel.confidence
                )
            )
            next_group_id += 1
        return results, next_group_id

    def execute(self, context: PipelineContext) -> PipelineContext:
        """Near 중복 탐지 실행."""
        debug_step(
            self._log_sink,
            "duplicate_detection_stage",
            {"stage": self.name}
        )

        if not context.request.enable_near or self._near_detector is None:
            return context

        if not context.blocking_groups or not context.file_entries_map:
            return context

        parse_by_store = _build_parse_by_store(context)
        near_results: list[DuplicateGroupResult] = []
        next_group_id = max(
            (r.group_id for r in context.results),
            default=0
        ) + 1

        for blocking_group in context.blocking_groups:
            group_results, next_group_id = self._process_blocking_group(
                blocking_group, context, parse_by_store, next_group_id
            )
            near_results.extend(group_results)

        debug_step(
            self._log_sink,
            "duplicate_detection_near_complete",
            {
                "near_groups_count": len(near_results),
                "total_near_files": sum(len(r.file_ids) for r in near_results)
            }
        )

        context.results = list(context.results) + near_results
        return context
