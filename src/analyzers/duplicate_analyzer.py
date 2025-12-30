"""
중복 파일 분석 모듈

파일 중복을 탐지하고 분석하는 기능을 제공합니다.
"""

from pathlib import Path
from typing import Optional, Any
import logging

from models.file_record import FileRecord
from utils.logger import get_logger
from utils.exceptions import DuplicateAnalysisError
from utils.hash_calculator import calculate_md5_hash
from utils.content_comparator import check_inclusion_with_anchors, check_range_inclusion
from utils.union_find import UnionFind
from analyzers.duplicate_group import DuplicateGroup


class DuplicateAnalyzer:
    """중복 파일 분석 클래스.
    
    파일 리스트를 분석하여 중복 그룹을 찾습니다.
    제목 기반 그룹핑 + 해시 기반 앵커를 사용한 효율적인 중복 탐지.
    
    Attributes:
        _logger: 로거 인스턴스
    """
    
    def __init__(self) -> None:
        """DuplicateAnalyzer 초기화."""
        self._logger = get_logger("DuplicateAnalyzer")
    
    def analyze(self, file_records: list[FileRecord]) -> list[list[FileRecord]]:
        """중복 파일을 분석하여 그룹으로 반환.
        
        Args:
            file_records: 분석할 FileRecord 리스트
        
        Returns:
            중복 그룹 리스트. 각 그룹은 FileRecord 리스트.
        
        Raises:
            DuplicateAnalysisError: 분석 중 오류 발생 시
        """
        try:
            self._logger.info(f"중복 분석 시작: {len(file_records)}개 파일")
            
            # 내부 분석 (근거 포함)
            duplicate_groups = self._analyze_internal(file_records)
            
            # list[list[FileRecord]]로 변환
            result = []
            for group in duplicate_groups:
                if len(group.members) > 1:
                    result.append(group.members)
            
            self._logger.info(f"중복 분석 완료: {len(result)}개 그룹 발견")
            return result
            
        except Exception as e:
            self._logger.error(f"중복 분석 오류: {e}", exc_info=True)
            raise DuplicateAnalysisError(f"중복 분석 중 오류 발생: {str(e)}") from e
    
    def _analyze_internal(self, records: list[FileRecord]) -> list[DuplicateGroup]:
        """내부 분석 메서드 (근거 포함).
        
        Args:
            records: 분석할 FileRecord 리스트
        
        Returns:
            DuplicateGroup 리스트
        """
        if not records:
            return []
        
        # 1. 정규화 제목별 그룹핑
        title_groups = self._group_by_normalized_title(records)
        
        all_groups: list[DuplicateGroup] = []
        all_edges: list[dict[str, Any]] = []
        
        # 2. 각 제목 그룹에 대해 중복 탐지
        for title, group_records in title_groups.items():
            if len(group_records) < 2:
                continue  # 혼자면 중복 아님
            
            self._logger.debug(f"제목 그룹 분석: '{title}' ({len(group_records)}개 파일)")
            
            # 2-1. 완전 동일 파일 탐지 (MD5)
            exact_groups, exact_edges = self._find_exact_duplicates(group_records)
            all_groups.extend(exact_groups)
            all_edges.extend(exact_edges)
            
            # 2-2. 포함 관계 중복 탐지
            inclusion_groups, inclusion_edges = self._find_inclusion_duplicates(group_records)
            all_groups.extend(inclusion_groups)
            all_edges.extend(inclusion_edges)
        
        # 3. Union-Find로 그룹 병합
        merged_groups = self._merge_groups_with_union_find(all_groups, all_edges, records)
        
        return merged_groups
    
    def _group_by_normalized_title(self, records: list[FileRecord]) -> dict[str, list[FileRecord]]:
        """정규화 제목별 그룹핑.
        
        Args:
            records: FileRecord 리스트
        
        Returns:
            {정규화_제목: [FileRecord 리스트]} 딕셔너리
        """
        groups: dict[str, list[FileRecord]] = {}
        
        for record in records:
            # normalized_title이 없으면 파일명을 그대로 사용
            key = record.normalized_title or record.name
            if key not in groups:
                groups[key] = []
            groups[key].append(record)
        
        return groups
    
    def _find_exact_duplicates(self, records: list[FileRecord]) -> tuple[list[DuplicateGroup], list[dict[str, Any]]]:
        """완전 동일 파일 탐지 (MD5).
        
        Args:
            records: FileRecord 리스트
        
        Returns:
            (DuplicateGroup 리스트, 엣지 리스트) 튜플
        """
        groups: list[DuplicateGroup] = []
        edges: list[dict[str, any]] = []
        
        # 해시 계산
        records_with_hash = self._calculate_hashes_for_group(records)
        
        # 해시별 그룹핑
        hash_groups: dict[str, list[FileRecord]] = {}
        for record in records_with_hash:
            if record.md5_hash:
                if record.md5_hash not in hash_groups:
                    hash_groups[record.md5_hash] = []
                hash_groups[record.md5_hash].append(record)
        
        # 중복 그룹 생성
        for hash_value, hash_records in hash_groups.items():
            if len(hash_records) > 1:
                group = DuplicateGroup(
                    members=hash_records,
                    reason="EXACT_MD5",
                    evidence={"md5_hash": hash_value},
                    confidence=1.0
                )
                groups.append(group)
                
                # 엣지 생성 (모든 쌍)
                for i in range(len(hash_records)):
                    for j in range(i + 1, len(hash_records)):
                        edges.append({
                            "file1": hash_records[i],
                            "file2": hash_records[j],
                            "reason": "EXACT_MD5",
                            "evidence": {"md5_hash": hash_value}
                        })
        
        return groups, edges
    
    def _find_inclusion_duplicates(self, records: list[FileRecord]) -> tuple[list[DuplicateGroup], list[dict[str, Any]]]:
        """포함 관계 중복 탐지.
        
        Args:
            records: FileRecord 리스트
        
        Returns:
            (DuplicateGroup 리스트, 엣지 리스트) 튜플
        """
        groups: list[DuplicateGroup] = []
        edges: list[dict[str, any]] = []
        
        # 크기 순 정렬
        sorted_records = sorted(records, key=lambda r: r.size)
        
        # 각 쌍에 대해 포함 관계 확인
        for i, small_record in enumerate(sorted_records):
            for large_record in sorted_records[i + 1:]:
                try:
                    # 회차 범위 확인
                    small_range = small_record.episode_range
                    large_range = large_record.episode_range
                    has_range = small_range is not None and large_range is not None
                    
                    # 범위 포함 확인 (있는 경우)
                    if has_range:
                        if not check_range_inclusion(small_range, large_range):
                            continue  # 범위 포함 안 되면 스킵
                    
                    # 포함 관계 확인
                    is_included, evidence = check_inclusion_with_anchors(
                        small_record.path,
                        large_record.path,
                        has_range=has_range,
                        small_range=small_range,
                        large_range=large_range
                    )
                    
                    if is_included:
                        reason = "RANGE_INCLUSION" if has_range else "CONTENT_INCLUSION"
                        confidence = 0.95 if has_range else 0.85
                        
                        # 엣지 생성
                        edge = {
                            "file1": small_record,
                            "file2": large_record,
                            "reason": reason,
                            "evidence": evidence
                        }
                        edges.append(edge)
                        
                        self._logger.debug(
                            f"포함 관계 발견: {small_record.name} → {large_record.name} "
                            f"(reason: {reason}, confidence: {confidence})"
                        )
                
                except Exception as e:
                    # 오류 시 스킵하고 계속 진행
                    self._logger.warning(
                        f"포함 관계 확인 중 오류 (스킵): {small_record.path} vs {large_record.path} - {e}"
                    )
                    continue
        
        # 엣지로부터 그룹 생성은 Union-Find에서 수행
        return groups, edges
    
    def _calculate_hashes_for_group(self, records: list[FileRecord]) -> list[FileRecord]:
        """그룹 내 해시 계산.
        
        Args:
            records: FileRecord 리스트
        
        Returns:
            해시가 계산된 FileRecord 리스트
        """
        result = []
        for record in records:
            # 이미 해시가 있으면 스킵
            if record.md5_hash:
                result.append(record)
                continue
            
            try:
                # MD5 해시 계산
                encoding = record.encoding if record.encoding != "-" else None
                md5_hash = calculate_md5_hash(record.path, encoding)
                
                # FileRecord 업데이트 (새 인스턴스 생성)
                updated_record = FileRecord(
                    path=record.path,
                    name=record.name,
                    size=record.size,
                    encoding=record.encoding,
                    title=record.title,
                    normalized_title=record.normalized_title,
                    episode_range=record.episode_range,
                    md5_hash=md5_hash,
                    normalized_hash=record.normalized_hash
                )
                result.append(updated_record)
            
            except Exception as e:
                # 해시 계산 실패 시 원본 유지
                self._logger.warning(f"해시 계산 실패 (스킵): {record.path} - {e}")
                result.append(record)
        
        return result
    
    def _merge_groups_with_union_find(
        self,
        groups: list[DuplicateGroup],
        edges: list[dict[str, Any]],
        all_records: list[FileRecord]
    ) -> list[DuplicateGroup]:
        """Union-Find로 그룹 병합.
        
        Args:
            groups: DuplicateGroup 리스트
            edges: 관계 엣지 리스트
            all_records: 전체 FileRecord 리스트
        
        Returns:
            병합된 DuplicateGroup 리스트
        """
        if not edges:
            return groups
        
        # FileRecord path → 인덱스 매핑 (path를 문자열로 변환하여 hashable하게 만듦)
        record_to_idx: dict[str, int] = {}
        for i, record in enumerate(all_records):
            record_to_idx[str(record.path)] = i
        
        # Union-Find 초기화
        uf = UnionFind(len(all_records))
        
        # 엣지로 Union-Find 수행
        for edge in edges:
            file1 = edge["file1"]
            file2 = edge["file2"]
            
            # path를 문자열로 변환하여 조회
            file1_path = str(file1.path)
            file2_path = str(file2.path)
            
            if file1_path in record_to_idx and file2_path in record_to_idx:
                idx1 = record_to_idx[file1_path]
                idx2 = record_to_idx[file2_path]
                uf.union(idx1, idx2)
        
        # 그룹별로 FileRecord 수집
        merged_groups: list[DuplicateGroup] = []
        uf_groups = uf.get_groups()
        
        for root_idx, member_indices in uf_groups.items():
            if len(member_indices) < 2:
                continue  # 혼자면 중복 아님
            
            # FileRecord 수집
            members = [all_records[idx] for idx in member_indices]
            
            # 대표 reason과 evidence 결정 (엣지에서)
            reason = "EXACT_MD5"  # 기본값
            evidence: dict[str, Any] = {}
            confidence = 1.0
            
            # 해당 그룹의 엣지 찾기 (path 기반 비교)
            member_paths = {str(m.path) for m in members}
            for edge in edges:
                file1 = edge["file1"]
                file2 = edge["file2"]
                file1_path = str(file1.path)
                file2_path = str(file2.path)
                if file1_path in member_paths and file2_path in member_paths:
                    reason = edge["reason"]
                    evidence = edge.get("evidence", {})
                    confidence = 0.95 if reason == "RANGE_INCLUSION" else 0.85
                    break
            
            group = DuplicateGroup(
                members=members,
                reason=reason,
                evidence=evidence,
                confidence=confidence
            )
            merged_groups.append(group)
        
        return merged_groups

