"""Near 중복 탐지 서비스."""
from pathlib import Path
from typing import TYPE_CHECKING, Optional, Protocol

from app.settings.constants import Constants
from domain.entities.file_entry import FileEntry
from domain.value_objects.blocking_group import BlockingGroup
from domain.value_objects.duplicate_relation import NearDuplicateRelation

if TYPE_CHECKING:
    from application.ports.log_sink import ILogSink
    from domain.value_objects.filename_parse_result import FilenameParseResult


class ISimHashService(Protocol):
    """SimHash 서비스 인터페이스 (Port).
    
    실제 구현은 Infrastructure 계층에서 제공 (v2 기능).
    """
    
    def calculate_simhash(self, file_path: Path) -> int:
        """SimHash 계산 (전체 파일).
        
        Args:
            file_path: 파일 경로.
        
        Returns:
            SimHash 값 (64비트 정수).
        """
        ...
    
    def calculate_simhash_from_samples(
        self,
        file_path: Path,
        sample_size: int = Constants.SAMPLE_SIZE
    ) -> int:
        """SimHash 계산 (샘플링 기반).
        
        Args:
            file_path: 파일 경로.
            sample_size: 샘플 크기 (바이트, 기본값: 64KB).
        
        Returns:
            SimHash 값 (64비트 정수).
        """
        ...
    
    def calculate_similarity(self, simhash1: int, simhash2: int) -> float:
        """SimHash 유사도 계산.
        
        Args:
            simhash1: 첫 번째 SimHash.
            simhash2: 두 번째 SimHash.
        
        Returns:
            유사도 (0.0 ~ 1.0).
        """
        ...


class NearDuplicateDetector:
    """Near 중복 탐지 서비스.
    
    내용이 거의 동일한 파일을 탐지하는 서비스.
    SimHash/MinHash 기반으로 유사도를 계산.
    """
    
    def __init__(
        self,
        simhash_service: Optional[ISimHashService] = None,
        similarity_threshold: float = Constants.DEFAULT_SIMILARITY_THRESHOLD,
        log_sink: Optional["ILogSink"] = None
    ) -> None:
        """NearDuplicateDetector 초기화.
        
        Args:
            simhash_service: SimHash 서비스 (Port, 선택적, v2 기능).
            similarity_threshold: 유사도 임계값 (기본값: 0.85).
            log_sink: 로그 싱크 (선택적, 디버깅 목적).
        """
        self._simhash_service = simhash_service
        self._similarity_threshold = similarity_threshold
        self._log_sink = log_sink
    
    def detect_near(
        self,
        blocking_group: BlockingGroup,
        file_entries: dict[int, FileEntry],
        parse_results: dict[int, "FilenameParseResult"]
    ) -> list[NearDuplicateRelation]:
        """Near 중복 탐지 (샘플링 기반).
        
        Args:
            blocking_group: Blocking Group.
            file_entries: 파일 ID -> FileEntry 매핑.
            parse_results: 파일 ID -> FilenameParseResult 매핑.
        
        Returns:
            NearDuplicateRelation 리스트.
        
        Note:
            SimHash 서비스가 없으면 빈 리스트 반환 (v2 기능).
            샘플링 기반으로 대용량 파일에서도 효율적으로 동작.
        """
        if self._simhash_service is None:
            return []  # SimHash 서비스가 없으면 Near 중복 탐지 불가 (v2 기능)
        
        near_relations = []
        
        # 같은 series_title_norm 그룹 내에서만 수행
        file_ids = blocking_group.file_ids
        
        # range_start가 같거나 overlap 높은 파일들만 비교 (효율성)
        candidate_pairs = []
        for i, file_id_a in enumerate(file_ids):
            if file_id_a not in file_entries or file_id_a not in parse_results:
                continue
            
            parse_a = parse_results[file_id_a]
            if not parse_a.has_range:
                continue  # 범위 정보가 없으면 건너뜀
            
            for file_id_b in file_ids[i + 1:]:
                if file_id_b not in file_entries or file_id_b not in parse_results:
                    continue
                
                parse_b = parse_results[file_id_b]
                if not parse_b.has_range:
                    continue
                
                # range_start가 같거나 overlap 높은 경우만 비교
                if parse_a.range_start == parse_b.range_start:
                    candidate_pairs.append((file_id_a, file_id_b))
                elif parse_a.has_range and parse_b.has_range:
                    # overlap 체크 (간단히 범위가 겹치면)
                    if not (parse_a.range_end < parse_b.range_start or parse_b.range_end < parse_a.range_start):
                        candidate_pairs.append((file_id_a, file_id_b))
        
        # 샘플링 기반 SimHash 비교
        for file_id_a, file_id_b in candidate_pairs:
            file_entry_a = file_entries[file_id_a]
            file_entry_b = file_entries[file_id_b]
            
            # 샘플링 기반 SimHash 계산 (앞/중간/끝 64KB)
            try:
                simhash_a = self._simhash_service.calculate_simhash_from_samples(
                    file_entry_a.path,
                    sample_size=Constants.SAMPLE_SIZE
                )
                simhash_b = self._simhash_service.calculate_simhash_from_samples(
                    file_entry_b.path,
                    sample_size=Constants.SAMPLE_SIZE
                )
            except Exception:
                # 파일 읽기 실패 시 건너뜀
                continue
            
            similarity = self._simhash_service.calculate_similarity(simhash_a, simhash_b)
            
            if similarity >= self._similarity_threshold:
                evidence = {
                    "simhash_a": simhash_a,
                    "simhash_b": simhash_b,
                    "similarity": similarity,
                    "method": "sampling_based",  # 샘플링 기반임을 명시
                    "sample_size_kb": 64
                }
                
                # 유사도가 높을수록 신뢰도 증가
                confidence = similarity
                
                relation = NearDuplicateRelation(
                    file_ids=[file_id_a, file_id_b],
                    similarity_score=similarity,
                    evidence=evidence,
                    confidence=confidence
                )
                near_relations.append(relation)
        
        return near_relations
