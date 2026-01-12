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
from domain.value_objects.filename_parse_result import FilenameParseResult


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
            # Blocking 그룹이 없으면 빈 결과로 반환
            context.results = []
            return context
        
        # 각 BlockingGroup 내에서 containment/version 관계 탐지
        group_results: list[DuplicateGroupResult] = []
        group_id = 0
        
        for blocking_group in context.blocking_groups:
            # BlockingGroup 내의 파일 ID를 FileDataStore file_id로 변환
            # blocking_group.file_ids는 원래 file_id (IndexRepository 또는 hash)
            # 이를 FileDataStore file_id로 변환해야 함
            store_file_ids: list[int] = []
            group_file_entries: dict[int, FileEntry] = {}  # FileDataStore file_id -> FileEntry
            group_parse_results: dict[int, FilenameParseResult] = {}  # FileDataStore file_id -> ParseResult
            
            for original_id in blocking_group.file_ids:
                # FileDataStore file_id로 변환
                store_file_id = context.file_id_mapping.get(original_id)
                if store_file_id is None:
                    continue
                
                store_file_ids.append(store_file_id)
                if store_file_id in context.file_entries_map:
                    group_file_entries[store_file_id] = context.file_entries_map[store_file_id]
                if original_id in context.parse_results:
                    group_parse_results[store_file_id] = context.parse_results[original_id]
            
            if len(store_file_ids) < 2:
                # 그룹에 파일이 2개 미만이면 스킵
                continue
            
            # 이후 로직은 store_file_ids 사용
            file_ids_list = store_file_ids
            
            # Containment 관계 추적용 (version 탐지 시 중복 방지)
            containment_relations: dict[int, list[int]] = defaultdict(list)  # container_id -> [contained_ids]
            
            # Containment 관계 탐지
            if context.request.enable_containment:
                for i, file_id_a in enumerate(file_ids_list):
                    if file_id_a not in group_file_entries or file_id_a not in group_parse_results:
                        continue
                    
                    for j, file_id_b in enumerate(file_ids_list):
                        if i >= j or file_id_b not in group_file_entries or file_id_b not in group_parse_results:
                            continue
                        
                        file_a = group_file_entries[file_id_a]
                        parse_a = group_parse_results[file_id_a]
                        file_b = group_file_entries[file_id_b]
                        parse_b = group_parse_results[file_id_b]
                        
                        # Containment 관계 탐지
                        containment_relation = self._containment_detector.detect_containment(
                            file_a, parse_a, file_b, parse_b
                        )
                        
                        if containment_relation:
                            # containment_relation의 file_id는 file_a.file_id와 file_b.file_id이므로
                            # file_id_mapping을 통해 FileDataStore file_id로 변환
                            container_store_id = context.file_id_mapping.get(containment_relation.container_file_id)
                            contained_store_id = context.file_id_mapping.get(containment_relation.contained_file_id)
                            
                            if container_store_id is None or contained_store_id is None:
                                continue
                            
                            containment_relations[container_store_id].append(contained_store_id)
            
            # Containment 그룹 생성 (container 기준으로 묶기)
            # 동일 container에 대해 여러 contained를 하나의 그룹으로 묶어 결과 폭증 방지
            if context.request.enable_containment:
                for container_store_id, contained_store_ids in containment_relations.items():
                    if not contained_store_ids:
                        continue
                    
                    # container와 모든 contained를 하나의 그룹으로 묶기
                    group_id += 1
                    containment_group = [container_store_id] + contained_store_ids
                    group_result = DuplicateGroupResult(
                        group_id=group_id,
                        duplicate_type="containment",
                        file_ids=containment_group,
                        recommended_keeper_id=container_store_id,
                        evidence={"contained_count": len(contained_store_ids)},
                        confidence=0.9  # containment는 높은 신뢰도
                    )
                    group_results.append(group_result)
            
            # Version 관계 탐지
            if context.request.enable_version:
                for i, file_id_a in enumerate(file_ids_list):
                    if file_id_a not in group_file_entries or file_id_a not in group_parse_results:
                        continue
                    
                    for j, file_id_b in enumerate(file_ids_list):
                        if i >= j or file_id_b not in group_file_entries or file_id_b not in group_parse_results:
                            continue
                        
                        # 이미 containment 관계가 있으면 스킵
                        if file_id_a in containment_relations.get(file_id_b, []):
                            continue
                        if file_id_b in containment_relations.get(file_id_a, []):
                            continue
                        
                        file_a = group_file_entries[file_id_a]
                        parse_a = group_parse_results[file_id_a]
                        file_b = group_file_entries[file_id_b]
                        parse_b = group_parse_results[file_id_b]
                        
                        # Version 관계 탐지
                        version_relation = self._containment_detector.detect_version(
                            file_a, parse_a, file_b, parse_b
                        )
                        
                        if version_relation:
                            # version_relation의 file_id는 원래 file_id이므로 FileDataStore file_id로 변환
                            newer_store_id = context.file_id_mapping.get(version_relation.newer_file_id)
                            older_store_id = context.file_id_mapping.get(version_relation.older_file_id)
                            
                            if newer_store_id is None or older_store_id is None:
                                continue
                            
                            # Version 그룹 생성 (FileDataStore file_id 사용)
                            group_id += 1
                            version_group = [newer_store_id, older_store_id]
                            group_result = DuplicateGroupResult(
                                group_id=group_id,
                                duplicate_type="version",
                                file_ids=version_group,
                                recommended_keeper_id=newer_store_id,
                                evidence=version_relation.evidence,
                                confidence=version_relation.confidence
                            )
                            group_results.append(group_result)
            
            # Exact/Near는 v2 기능이므로 지금은 스킵
            # TODO: enable_exact/enable_near 플래그 처리 (IHashService 필요)
        
        context.results = group_results
        
        return context
