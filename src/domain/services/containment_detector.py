"""포함/버전 관계 탐지 서비스."""
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from domain.entities.file_entry import FileEntry

# Sonar S1192: 공통 경고 메시지 상수
WARNING_RANGE_INCREASED_SIZE_DECREASED = (
    "범위는 증가했지만 크기는 감소했습니다. 압축/정리본일 수 있습니다."
)
from domain.value_objects.duplicate_relation import ContainmentRelation, VersionRelation
from domain.value_objects.filename_parse_result import FilenameParseResult
from domain.value_objects.range_segment import RangeSegment

if TYPE_CHECKING:
    from application.ports.log_sink import ILogSink


class ContainmentDetector:
    """포함/버전 관계 탐지 서비스.
    
    파일명 파싱 결과를 기반으로 포함 관계 및 버전 관계를 탐지하는 서비스.
    내용을 읽지 않고도 판정 가능 (파일명과 메타데이터만으로 판정).
    """
    
    def __init__(self, log_sink: Optional["ILogSink"] = None) -> None:
        """ContainmentDetector 초기화.

        Args:
            log_sink: 로그 싱크 (선택적, 디버깅 목적).
        """
        self._log_sink = log_sink

    def _get_containment_file_ids(
        self,
        file_a: FileEntry,
        file_b: FileEntry,
        parse_a: FilenameParseResult,
        parse_b: FilenameParseResult,
    ) -> Optional[tuple[str, str]]:
        """동일 작품·범위·file_id 검증 후 (file_id_a, file_id_b) 반환."""
        if not parse_a.is_same_series(parse_b):
            return None
        if not (parse_a.has_range and parse_b.has_range):
            return None
        if file_a.file_id is None or file_b.file_id is None:
            return None
        return (file_a.file_id, file_b.file_id)

    def _containment_confidence(
        self, parse_container: FilenameParseResult, parse_contained: FilenameParseResult
    ) -> float:
        """포함 관계 신뢰도 (완결 포함이면 0.95, 아니면 0.9)."""
        if parse_container.is_complete and not parse_contained.is_complete:
            return 0.95
        return 0.9

    def _evidence_segments(
        self, parse_a: FilenameParseResult, parse_b: FilenameParseResult
    ) -> dict:
        """세그먼트 기반 evidence 딕셔너리."""
        return {
            "segments_a": [(s.segment_type, s.start, s.end, s.unit) for s in parse_a.segments],
            "segments_b": [(s.segment_type, s.start, s.end, s.unit) for s in parse_b.segments],
            "tags_a": parse_a.tags,
            "tags_b": parse_b.tags,
        }

    def _evidence_range(
        self, parse_a: FilenameParseResult, parse_b: FilenameParseResult
    ) -> dict:
        """범위 기반 evidence 딕셔너리."""
        return {
            "range_a": (parse_a.range_start, parse_a.range_end),
            "range_b": (parse_b.range_start, parse_b.range_end),
            "tags_a": parse_a.tags,
            "tags_b": parse_b.tags,
        }

    def _try_containment_via_segments(
        self,
        file_id_a: str,
        file_id_b: str,
        parse_a: FilenameParseResult,
        parse_b: FilenameParseResult,
    ) -> Optional[ContainmentRelation]:
        """세그먼트로 포함 관계 탐지. 없으면 None."""
        segs_b_by_type: dict[str, list[RangeSegment]] = defaultdict(list)
        for s in parse_b.segments:
            segs_b_by_type[s.segment_type].append(s)
        for seg_a in parse_a.segments:
            for seg_b in segs_b_by_type.get(seg_a.segment_type, []):
                if seg_a.contains(seg_b):
                    evidence = self._evidence_segments(parse_a, parse_b)
                    confidence = self._containment_confidence(parse_a, parse_b)
                    return ContainmentRelation(
                        container_file_id=file_id_a,
                        contained_file_id=file_id_b,
                        evidence=evidence,
                        confidence=confidence,
                    )
                if seg_b.contains(seg_a):
                    evidence = self._evidence_segments(parse_a, parse_b)
                    confidence = self._containment_confidence(parse_b, parse_a)
                    return ContainmentRelation(
                        container_file_id=file_id_b,
                        contained_file_id=file_id_a,
                        evidence=evidence,
                        confidence=confidence,
                    )
        return None

    def _try_containment_via_range(
        self,
        file_id_a: str,
        file_id_b: str,
        parse_a: FilenameParseResult,
        parse_b: FilenameParseResult,
    ) -> Optional[ContainmentRelation]:
        """범위로 포함 관계 탐지. 없으면 None."""
        if parse_a.range_contains(parse_b):
            return ContainmentRelation(
                container_file_id=file_id_a,
                contained_file_id=file_id_b,
                evidence=self._evidence_range(parse_a, parse_b),
                confidence=self._containment_confidence(parse_a, parse_b),
            )
        if parse_b.range_contains(parse_a):
            return ContainmentRelation(
                container_file_id=file_id_b,
                contained_file_id=file_id_a,
                evidence=self._evidence_range(parse_a, parse_b),
                confidence=self._containment_confidence(parse_b, parse_a),
            )
        return None

    def detect_containment(
        self,
        file_a: FileEntry,
        parse_a: FilenameParseResult,
        file_b: FileEntry,
        parse_b: FilenameParseResult,
    ) -> Optional[ContainmentRelation]:
        """포함 관계 탐지.

        Args:
            file_a: 첫 번째 파일.
            parse_a: 첫 번째 파일의 파싱 결과.
            file_b: 두 번째 파일.
            parse_b: 두 번째 파일의 파싱 결과.

        Returns:
            포함 관계가 발견되면 ContainmentRelation, 없으면 None.
        """
        ids = self._get_containment_file_ids(file_a, file_b, parse_a, parse_b)
        if ids is None:
            return None
        file_id_a, file_id_b = ids

        if parse_a.has_segments and parse_b.has_segments:
            result = self._try_containment_via_segments(
                file_id_a, file_id_b, parse_a, parse_b
            )
            if result is not None:
                return result

        return self._try_containment_via_range(
            file_id_a, file_id_b, parse_a, parse_b
        )
    
    def _version_confidence_and_warning(
        self,
        newer_size: int,
        older_size: int,
        newer_mtime: datetime,
        older_mtime: datetime,
        evidence: dict,
    ) -> float:
        """버전 관계 신뢰도 계산. 크기 감소 시 경고 추가 후 0.7, 아니면 0.85~0.9."""
        if newer_size >= older_size:
            confidence = 0.85
            if newer_mtime > older_mtime:
                confidence = 0.9
            return confidence
        evidence["warning"] = "end_increased_but_size_decreased"
        evidence["warning_message"] = WARNING_RANGE_INCREASED_SIZE_DECREASED
        return 0.7

    def _evidence_version_segments(
        self,
        file_a: FileEntry,
        file_b: FileEntry,
        parse_a: FilenameParseResult,
        parse_b: FilenameParseResult,
    ) -> dict:
        """버전 판정용 세그먼트 evidence."""
        return {
            "segments_a": [(s.segment_type, s.start, s.end, s.unit) for s in parse_a.segments],
            "segments_b": [(s.segment_type, s.start, s.end, s.unit) for s in parse_b.segments],
            "size_a": file_a.size,
            "size_b": file_b.size,
            "mtime_a": file_a.mtime.isoformat(),
            "mtime_b": file_b.mtime.isoformat(),
        }

    def _evidence_version_range(
        self,
        file_a: FileEntry,
        file_b: FileEntry,
        parse_a: FilenameParseResult,
        parse_b: FilenameParseResult,
    ) -> dict:
        """버전 판정용 범위 evidence."""
        return {
            "range_a": (parse_a.range_start, parse_a.range_end),
            "range_b": (parse_b.range_start, parse_b.range_end),
            "size_a": file_a.size,
            "size_b": file_b.size,
            "mtime_a": file_a.mtime.isoformat(),
            "mtime_b": file_b.mtime.isoformat(),
        }

    def _try_version_via_segments(
        self,
        file_id_a: str,
        file_id_b: str,
        file_a: FileEntry,
        file_b: FileEntry,
        parse_a: FilenameParseResult,
        parse_b: FilenameParseResult,
    ) -> Optional[VersionRelation]:
        """세그먼트로 버전 관계 탐지. 없으면 None."""
        primary_a = parse_a.primary_segment
        primary_b = parse_b.primary_segment
        if primary_a is None or primary_b is None:
            return None
        if primary_a.start != primary_b.start or primary_a.end == primary_b.end:
            return None

        evidence = self._evidence_version_segments(file_a, file_b, parse_a, parse_b)

        if primary_a.end > primary_b.end:
            confidence = self._version_confidence_and_warning(
                file_a.size, file_b.size, file_a.mtime, file_b.mtime, evidence
            )
            return VersionRelation(
                newer_file_id=file_id_a,
                older_file_id=file_id_b,
                evidence=evidence,
                confidence=confidence,
            )
        if primary_b.end > primary_a.end:
            confidence = self._version_confidence_and_warning(
                file_b.size, file_a.size, file_b.mtime, file_a.mtime, evidence
            )
            return VersionRelation(
                newer_file_id=file_id_b,
                older_file_id=file_id_a,
                evidence=evidence,
                confidence=confidence,
            )
        return None

    def _try_version_via_range(
        self,
        file_id_a: str,
        file_id_b: str,
        file_a: FileEntry,
        file_b: FileEntry,
        parse_a: FilenameParseResult,
        parse_b: FilenameParseResult,
    ) -> Optional[VersionRelation]:
        """범위로 버전 관계 탐지. 없으면 None."""
        if parse_a.range_start != parse_b.range_start:
            return None
        if parse_a.range_end == parse_b.range_end:
            return None

        evidence = self._evidence_version_range(file_a, file_b, parse_a, parse_b)

        if parse_a.range_end > parse_b.range_end:
            confidence = self._version_confidence_and_warning(
                file_a.size, file_b.size, file_a.mtime, file_b.mtime, evidence
            )
            return VersionRelation(
                newer_file_id=file_id_a,
                older_file_id=file_id_b,
                evidence=evidence,
                confidence=confidence,
            )
        if parse_b.range_end > parse_a.range_end:
            confidence = self._version_confidence_and_warning(
                file_b.size, file_a.size, file_b.mtime, file_a.mtime, evidence
            )
            return VersionRelation(
                newer_file_id=file_id_b,
                older_file_id=file_id_a,
                evidence=evidence,
                confidence=confidence,
            )
        return None

    def detect_version(
        self,
        file_a: FileEntry,
        parse_a: FilenameParseResult,
        file_b: FileEntry,
        parse_b: FilenameParseResult,
    ) -> Optional[VersionRelation]:
        """버전 관계 탐지.

        Args:
            file_a: 첫 번째 파일.
            parse_a: 첫 번째 파일의 파싱 결과.
            file_b: 두 번째 파일.
            parse_b: 두 번째 파일의 파싱 결과.

        Returns:
            버전 관계가 발견되면 VersionRelation, 없으면 None.
        """
        ids = self._get_containment_file_ids(file_a, file_b, parse_a, parse_b)
        if ids is None:
            return None
        file_id_a, file_id_b = ids

        if parse_a.has_segments and parse_b.has_segments:
            result = self._try_version_via_segments(
                file_id_a, file_id_b, file_a, file_b, parse_a, parse_b
            )
            if result is not None:
                return result

        return self._try_version_via_range(
            file_id_a, file_id_b, file_a, file_b, parse_a, parse_b
        )
