"""포함/버전 관계 탐지 서비스."""
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from domain.entities.file_entry import FileEntry
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
    
    def detect_containment(
        self,
        file_a: FileEntry,
        parse_a: FilenameParseResult,
        file_b: FileEntry,
        parse_b: FilenameParseResult
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
        
        # 같은 작품인지 확인
        if not parse_a.is_same_series(parse_b):
            return None
        
        # 범위 정보가 모두 있어야 함
        if not (parse_a.has_range and parse_b.has_range):
            return None
        
        # file_id가 없으면 관계 탐지 불가 (Worker 단계에서 file_id 보장 필요)
        if file_a.file_id is None or file_b.file_id is None:
            return None
        
        file_id_a = file_a.file_id
        file_id_b = file_b.file_id
        
        # segments 기반 포함 관계 판정 (우선)
        if parse_a.has_segments and parse_b.has_segments:
            # 같은 타입의 세그먼트끼리 비교
            for seg_a in parse_a.segments:
                for seg_b in parse_b.segments:
                    if seg_a.segment_type == seg_b.segment_type:
                        # A가 B를 포함하는지 확인
                        if seg_a.contains(seg_b):
                            evidence = {
                                "segments_a": [(s.segment_type, s.start, s.end, s.unit) for s in parse_a.segments],
                                "segments_b": [(s.segment_type, s.start, s.end, s.unit) for s in parse_b.segments],
                                "tags_a": parse_a.tags,
                                "tags_b": parse_b.tags
                            }
                            
                            confidence = 0.9
                            
                            # 완결 태그가 있으면 신뢰도 증가
                            if parse_a.is_complete and not parse_b.is_complete:
                                confidence = 0.95
                            
                            return ContainmentRelation(
                                container_file_id=file_id_a,
                                contained_file_id=file_id_b,
                                evidence=evidence,
                                confidence=confidence
                            )
                        
                        # B가 A를 포함하는지 확인
                        if seg_b.contains(seg_a):
                            evidence = {
                                "segments_a": [(s.segment_type, s.start, s.end, s.unit) for s in parse_a.segments],
                                "segments_b": [(s.segment_type, s.start, s.end, s.unit) for s in parse_b.segments],
                                "tags_a": parse_a.tags,
                                "tags_b": parse_b.tags
                            }
                            
                            confidence = 0.9
                            
                            if parse_b.is_complete and not parse_a.is_complete:
                                confidence = 0.95
                            
                            return ContainmentRelation(
                                container_file_id=file_id_b,
                                contained_file_id=file_id_a,
                                evidence=evidence,
                                confidence=confidence
                            )
        
        # 기존 방식 (하위 호환성): range_start/range_end 기반
        # A가 B를 포함하는지 확인
        if parse_a.range_contains(parse_b):
            evidence = {
                "range_a": (parse_a.range_start, parse_a.range_end),
                "range_b": (parse_b.range_start, parse_b.range_end),
                "tags_a": parse_a.tags,
                "tags_b": parse_b.tags
            }
            
            confidence = 0.9
            
            # 완결 태그가 있으면 신뢰도 증가
            if parse_a.is_complete and not parse_b.is_complete:
                confidence = 0.95
            
            return ContainmentRelation(
                container_file_id=file_id_a,
                contained_file_id=file_id_b,
                evidence=evidence,
                confidence=confidence
            )
        
        # B가 A를 포함하는지 확인
        if parse_b.range_contains(parse_a):
            evidence = {
                "range_a": (parse_a.range_start, parse_a.range_end),
                "range_b": (parse_b.range_start, parse_b.range_end),
                "tags_a": parse_a.tags,
                "tags_b": parse_b.tags
            }
            
            confidence = 0.9
            
            if parse_b.is_complete and not parse_a.is_complete:
                confidence = 0.95
            
            return ContainmentRelation(
                container_file_id=file_id_b,
                contained_file_id=file_id_a,
                evidence=evidence,
                confidence=confidence
            )
        
        return None
    
    def detect_version(
        self,
        file_a: FileEntry,
        parse_a: FilenameParseResult,
        file_b: FileEntry,
        parse_b: FilenameParseResult
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
        
        # 같은 작품인지 확인
        if not parse_a.is_same_series(parse_b):
            return None
        
        # 범위 정보가 모두 있어야 함
        if not (parse_a.has_range and parse_b.has_range):
            return None
        
        # file_id가 없으면 관계 탐지 불가 (Worker 단계에서 file_id 보장 필요)
        if file_a.file_id is None or file_b.file_id is None:
            return None
        
        file_id_a = file_a.file_id
        file_id_b = file_b.file_id
        
        # segments 기반 판정 (우선)
        if parse_a.has_segments and parse_b.has_segments:
            # primary segment만 비교 (버전 관계는 primary segment 기준)
            primary_a = parse_a.primary_segment
            primary_b = parse_b.primary_segment
            
            if primary_a is None or primary_b is None:
                return None
            
            # 시작 범위가 같아야 함 (버전 관계 조건)
            if primary_a.start != primary_b.start:
                return None
            
            # 끝 범위가 달라야 함
            if primary_a.end == primary_b.end:
                return None
            
            evidence = {
                "segments_a": [(s.segment_type, s.start, s.end, s.unit) for s in parse_a.segments],
                "segments_b": [(s.segment_type, s.start, s.end, s.unit) for s in parse_b.segments],
                "size_a": file_a.size,
                "size_b": file_b.size,
                "mtime_a": file_a.mtime.isoformat(),
                "mtime_b": file_b.mtime.isoformat()
            }
            
            # A가 B보다 새로운 버전인지 확인
            if primary_a.end > primary_b.end:
                confidence = 0.85
                
                # 범위가 증가했고, 크기도 증가했으면 버전 관계
                if file_a.size >= file_b.size:
                    # 수정일도 더 최신이면 신뢰도 증가
                    if file_a.mtime > file_b.mtime:
                        confidence = 0.9
                else:
                    # size 감소 케이스 경고
                    evidence["warning"] = "end_increased_but_size_decreased"
                    evidence["warning_message"] = "범위는 증가했지만 크기는 감소했습니다. 압축/정리본일 수 있습니다."
                    confidence = 0.7  # 신뢰도 낮춤
                
                return VersionRelation(
                    newer_file_id=file_id_a,
                    older_file_id=file_id_b,
                    evidence=evidence,
                    confidence=confidence
                )
            
            # B가 A보다 새로운 버전인지 확인
            if primary_b.end > primary_a.end:
                confidence = 0.85
                
                if file_b.size >= file_a.size:
                    if file_b.mtime > file_a.mtime:
                        confidence = 0.9
                else:
                    # size 감소 케이스 경고
                    evidence["warning"] = "end_increased_but_size_decreased"
                    evidence["warning_message"] = "범위는 증가했지만 크기는 감소했습니다. 압축/정리본일 수 있습니다."
                    confidence = 0.7  # 신뢰도 낮춤
                
                return VersionRelation(
                    newer_file_id=file_id_b,
                    older_file_id=file_id_a,
                    evidence=evidence,
                    confidence=confidence
                )
            
            return None
        
        # 기존 방식 (하위 호환성): range_start/range_end 기반
        # 시작 범위가 같아야 함 (버전 관계 조건)
        if parse_a.range_start != parse_b.range_start:
            return None
        
        # 끝 범위가 달라야 함
        if parse_a.range_end == parse_b.range_end:
            return None
        
        evidence = {
            "range_a": (parse_a.range_start, parse_a.range_end),
            "range_b": (parse_b.range_start, parse_b.range_end),
            "size_a": file_a.size,
            "size_b": file_b.size,
            "mtime_a": file_a.mtime.isoformat(),
            "mtime_b": file_b.mtime.isoformat()
        }
        
        # A가 B보다 새로운 버전인지 확인
        if parse_a.range_end > parse_b.range_end:
            # 범위가 증가했고, 크기도 증가했으면 버전 관계
            if file_a.size >= file_b.size:
                confidence = 0.85
                
                # 수정일도 더 최신이면 신뢰도 증가
                if file_a.mtime > file_b.mtime:
                    confidence = 0.9
                
                return VersionRelation(
                    newer_file_id=file_id_a,
                    older_file_id=file_id_b,
                    evidence=evidence,
                    confidence=confidence
                )
            
            # size 감소 케이스 경고
            if file_a.size < file_b.size:
                evidence["warning"] = "end_increased_but_size_decreased"
                evidence["warning_message"] = "범위는 증가했지만 크기는 감소했습니다. 압축/정리본일 수 있습니다."
                
                confidence = 0.7  # 신뢰도 낮춤
                
                return VersionRelation(
                    newer_file_id=file_id_a,
                    older_file_id=file_id_b,
                    evidence=evidence,
                    confidence=confidence
                )
        
        # B가 A보다 새로운 버전인지 확인
        if parse_b.range_end > parse_a.range_end:
            if file_b.size >= file_a.size:
                confidence = 0.85
                
                if file_b.mtime > file_a.mtime:
                    confidence = 0.9
                
                return VersionRelation(
                    newer_file_id=file_id_b,
                    older_file_id=file_id_a,
                    evidence=evidence,
                    confidence=confidence
                )
            
            # size 감소 케이스 경고
            if file_b.size < file_a.size:
                evidence["warning"] = "end_increased_but_size_decreased"
                evidence["warning_message"] = "범위는 증가했지만 크기는 감소했습니다. 압축/정리본일 수 있습니다."
                
                confidence = 0.7
                
                return VersionRelation(
                    newer_file_id=file_id_b,
                    older_file_id=file_id_a,
                    evidence=evidence,
                    confidence=confidence
                )
        
        return None
