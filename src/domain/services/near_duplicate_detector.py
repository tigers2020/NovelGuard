"""Near 중복 탐지 서비스."""

from typing import TYPE_CHECKING, Optional

from domain.entities.file_entry import FileEntry
from domain.ports.sim_hash import ISimHashService
from domain.value_objects.blocking_group import BlockingGroup
from domain.value_objects.detection_config import DetectionDefaults
from domain.value_objects.duplicate_relation import NearDuplicateRelation

if TYPE_CHECKING:
    from domain.value_objects.filename_parse_result import FilenameParseResult


class NearDuplicateDetector:
    """Near 중복 탐지 서비스.

    내용이 거의 동일한 파일을 탐지하는 서비스.
    SimHash/MinHash 기반으로 유사도를 계산.
    """

    def __init__(
        self,
        simhash_service: Optional[ISimHashService] = None,
        similarity_threshold: float = DetectionDefaults.DEFAULT_SIMILARITY_THRESHOLD,
    ) -> None:
        """NearDuplicateDetector 초기화.

        Args:
            simhash_service: SimHash 서비스 (Port, 선택적, v2 기능).
            similarity_threshold: 유사도 임계값 (기본값: 0.85).
        """
        self._simhash_service = simhash_service
        self._similarity_threshold = similarity_threshold

    @staticmethod
    def _parse_with_range_if_present(
        file_id: int,
        file_entries: dict[int, FileEntry],
        parse_results: dict[int, "FilenameParseResult"],
    ) -> Optional["FilenameParseResult"]:
        if file_id not in file_entries or file_id not in parse_results:
            return None
        pr = parse_results[file_id]
        if not pr.has_range:
            return None
        return pr

    @staticmethod
    def _pair_is_simhash_candidate(
        parse_a: "FilenameParseResult", parse_b: "FilenameParseResult"
    ) -> bool:
        if parse_a.range_start == parse_b.range_start:
            return True
        a0, a1 = parse_a.range_start, parse_a.range_end
        b0, b1 = parse_b.range_start, parse_b.range_end
        if a0 is None or a1 is None or b0 is None or b1 is None:
            return False
        return not (a1 < b0 or b1 < a0)

    def _pairs_for_anchor(
        self,
        file_id_a: int,
        parse_a: "FilenameParseResult",
        successor_ids: list[int],
        file_entries: dict[int, FileEntry],
        parse_results: dict[int, "FilenameParseResult"],
    ) -> list[tuple[int, int]]:
        out: list[tuple[int, int]] = []
        for file_id_b in successor_ids:
            parse_b = self._parse_with_range_if_present(file_id_b, file_entries, parse_results)
            if parse_b is None:
                continue
            if self._pair_is_simhash_candidate(parse_a, parse_b):
                out.append((file_id_a, file_id_b))
        return out

    def _collect_candidate_pairs(
        self,
        file_ids: list[int],
        file_entries: dict[int, FileEntry],
        parse_results: dict[int, "FilenameParseResult"],
    ) -> list[tuple[int, int]]:
        pairs: list[tuple[int, int]] = []
        for i, file_id_a in enumerate(file_ids):
            parse_a = self._parse_with_range_if_present(file_id_a, file_entries, parse_results)
            if parse_a is None:
                continue
            pairs.extend(
                self._pairs_for_anchor(
                    file_id_a,
                    parse_a,
                    file_ids[i + 1 :],
                    file_entries,
                    parse_results,
                )
            )
        return pairs

    def _relation_from_pair_if_similar(
        self,
        simhash_service: "ISimHashService",
        file_id_a: int,
        file_id_b: int,
        file_entries: dict[int, FileEntry],
    ) -> Optional[NearDuplicateRelation]:
        file_entry_a = file_entries[file_id_a]
        file_entry_b = file_entries[file_id_b]
        try:
            simhash_a = simhash_service.calculate_simhash_from_samples(
                file_entry_a.path, sample_size=DetectionDefaults.SAMPLE_SIZE
            )
            simhash_b = simhash_service.calculate_simhash_from_samples(
                file_entry_b.path, sample_size=DetectionDefaults.SAMPLE_SIZE
            )
        except (OSError, ValueError):
            return None
        similarity = simhash_service.calculate_similarity(simhash_a, simhash_b)
        if similarity < self._similarity_threshold:
            return None
        evidence = {
            "simhash_a": simhash_a,
            "simhash_b": simhash_b,
            "similarity": similarity,
            "method": "sampling_based",
            "sample_size_kb": 64,
        }
        return NearDuplicateRelation(
            file_ids=[file_id_a, file_id_b],
            similarity_score=similarity,
            evidence=evidence,
            confidence=similarity,
        )

    def detect_near(
        self,
        blocking_group: BlockingGroup,
        file_entries: dict[int, FileEntry],
        parse_results: dict[int, "FilenameParseResult"],
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
        simhash_service = self._simhash_service
        if simhash_service is None:
            return []

        candidate_pairs = self._collect_candidate_pairs(
            blocking_group.file_ids, file_entries, parse_results
        )
        near_relations: list[NearDuplicateRelation] = []
        for file_id_a, file_id_b in candidate_pairs:
            relation = self._relation_from_pair_if_similar(
                simhash_service, file_id_a, file_id_b, file_entries
            )
            if relation is not None:
                near_relations.append(relation)
        return near_relations
