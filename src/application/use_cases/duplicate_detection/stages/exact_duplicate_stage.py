"""Exact(완전 동일) 중복 탐지 단계."""
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
from domain.services.exact_duplicate_detector import ExactDuplicateDetector
from domain.value_objects.blocking_group import BlockingGroup


class ExactDuplicateStage(PipelineStage):
    """Exact 중복 탐지 단계.

    파일 크기로 그룹을 만든 뒤, 동일 크기 파일들에 대해 해시 기반 완전 동일 탐지를 수행합니다.
    파싱/작품명에 의존하지 않아, 파일명이 달라도 내용이 같으면 탐지됩니다.
    """

    def __init__(
        self,
        exact_detector: Optional[ExactDuplicateDetector] = None,
        log_sink: Optional[ILogSink] = None
    ) -> None:
        """Exact 중복 단계 초기화.

        Args:
            exact_detector: Exact 중복 탐지기 (None이면 이 단계는 no-op).
            log_sink: 로그 싱크 (선택적).
        """
        self._exact_detector = exact_detector
        self._log_sink = log_sink

    @property
    def name(self) -> str:
        return "Exact 중복 탐지"

    def execute(self, context: PipelineContext) -> PipelineContext:
        """Exact 중복 탐지 실행."""
        debug_step(
            self._log_sink,
            "duplicate_detection_stage",
            {"stage": self.name}
        )

        if not context.request.enable_exact or self._exact_detector is None:
            return context

        if not context.file_entries_map:
            return context

        # 크기별로 그룹화 (동일 크기만 비교)
        size_to_ids: dict[int, list[int]] = defaultdict(list)
        for file_id, entry in context.file_entries_map.items():
            size_to_ids[entry.size].append(file_id)

        exact_results: list[DuplicateGroupResult] = []
        next_group_id = max(
            (r.group_id for r in context.results),
            default=0
        ) + 1

        for size, file_ids in size_to_ids.items():
            if len(file_ids) < 2:
                continue
            synthetic_group = BlockingGroup(
                series_title_norm="",
                extension="",
                file_ids=file_ids,
                range_start=None
            )
            relations = self._exact_detector.detect_exact(
                synthetic_group,
                context.file_entries_map
            )
            for rel in relations:
                # 추천 keeper: 수정일이 가장 최신인 파일
                keeper_id = self._pick_keeper(rel.file_ids, context.file_entries_map)
                exact_results.append(
                    DuplicateGroupResult(
                        group_id=next_group_id,
                        duplicate_type="exact",
                        file_ids=rel.file_ids,
                        recommended_keeper_id=keeper_id,
                        evidence=dict(rel.evidence),
                        confidence=rel.confidence
                    )
                )
                next_group_id += 1

        debug_step(
            self._log_sink,
            "duplicate_detection_exact_complete",
            {
                "exact_groups_count": len(exact_results),
                "total_exact_files": sum(len(r.file_ids) for r in exact_results)
            }
        )

        context.results = list(context.results) + exact_results
        return context

    @staticmethod
    def _pick_keeper(
        file_ids: list[int],
        file_entries_map: dict[int, FileEntry]
    ) -> int:
        """수정일이 가장 최신인 파일 ID 반환."""
        best_id = file_ids[0]
        best_mtime = None
        for fid in file_ids:
            entry = file_entries_map.get(fid)
            if entry and (best_mtime is None or entry.mtime > best_mtime):
                best_mtime = entry.mtime
                best_id = fid
        return best_id
