"""
중복 파일 분석 모듈

파일 중복을 탐지하고 분석하는 기능을 제공합니다.
최신본 기준 중복 판별기: base_title 그룹핑 → 최신본 선택 → 포함 관계 검증 파이프라인.
"""

from pathlib import Path
from typing import Optional, Any, Callable
from collections import defaultdict
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import os

from models.file_record import FileRecord
from utils.logger import get_logger
from utils.exceptions import DuplicateAnalysisError
from utils.hash_calculator import compute_anchor_hashes
from utils.constants import (
    MIN_FILE_SIZE,
    MAX_WORKER_THREADS,
    PROGRESS_UPDATE_INTERVAL,
    GROUP_PROGRESS_UPDATE_INTERVAL,
    SIZE_DIFFERENCE_THRESHOLD,
    CONFIDENCE_STRONG,
    CONFIDENCE_WEAK,
    DEFAULT_ENCODING,
    ENCODING_NOT_DETECTED,
)
from analyzers.duplicate_group import DuplicateGroup


class DuplicateAnalyzer:
    """중복 파일 분석 클래스.
    
    웹소설 묶음 파일에 특화된 "최신본 기준 중복 판별기"입니다.
    base_title 기준 그룹핑 → 최신본 선택 → anchor_hashes 기반 포함 관계 검증을 수행합니다.
    
    Attributes:
        _logger: 로거 인스턴스
        _progress_callback: 진행 상황 업데이트 콜백 함수 (선택적)
    """
    
    def __init__(self, progress_callback: Optional[Callable[[str], None]] = None) -> None:
        """DuplicateAnalyzer 초기화.
        
        Args:
            progress_callback: 진행 상황 업데이트 콜백 함수 (message: str) -> None
        """
        self._logger = get_logger("DuplicateAnalyzer")
        self._progress_callback = progress_callback
    
    def _update_progress(self, message: str) -> None:
        """진행 상황을 업데이트합니다.
        
        Args:
            message: 진행 상황 메시지
        """
        if self._progress_callback:
            self._progress_callback(message)
        self._logger.debug(message)
    
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
            self._update_progress(f"중복 분석 시작: {len(file_records)}개 파일")
            
            # 내부 분석 (근거 포함)
            duplicate_groups = self._analyze_internal(file_records)
            
            # list[list[FileRecord]]로 변환
            result = []
            for group in duplicate_groups:
                if len(group.members) > 1:
                    result.append(group.members)
            
            self._logger.info(f"중복 분석 완료: {len(result)}개 그룹 발견")
            self._update_progress(f"중복 분석 완료: {len(result)}개 그룹 발견")
            return result
            
        except Exception as e:
            self._logger.error(f"중복 분석 오류: {e}", exc_info=True)
            raise DuplicateAnalysisError(f"중복 분석 중 오류 발생: {str(e)}") from e
    
    def analyze_with_groups(self, file_records: list[FileRecord]) -> list[DuplicateGroup]:
        """중복 파일을 분석하여 DuplicateGroup 리스트로 반환.
        
        keep_file 정보를 포함한 완전한 그룹 정보를 반환합니다.
        
        Args:
            file_records: 분석할 FileRecord 리스트
        
        Returns:
            DuplicateGroup 리스트 (members가 2개 이상인 그룹만)
        
        Raises:
            DuplicateAnalysisError: 분석 중 오류 발생 시
        """
        try:
            self._logger.info(f"중복 분석 시작 (그룹 정보 포함): {len(file_records)}개 파일")
            self._update_progress(f"중복 분석 시작: {len(file_records)}개 파일")
            
            # 내부 분석 (근거 포함)
            duplicate_groups = self._analyze_internal(file_records)
            
            # members가 2개 이상인 그룹만 필터링
            result = [group for group in duplicate_groups if len(group.members) > 1]
            
            self._logger.info(f"중복 분석 완료: {len(result)}개 그룹 발견")
            self._update_progress(f"중복 분석 완료: {len(result)}개 그룹 발견")
            return result
            
        except Exception as e:
            self._logger.error(f"중복 분석 오류: {e}", exc_info=True)
            raise DuplicateAnalysisError(f"중복 분석 중 오류 발생: {str(e)}") from e
    
    def _analyze_internal(self, records: list[FileRecord]) -> list[DuplicateGroup]:
        """내부 분석 메서드 (최신본 기준 중복 판별 파이프라인).
        
        Phase 1: base_title 기준 그룹핑 (없으면 head anchor 버킷)
        Phase 2: 각 그룹에서 최신본 선택
        Phase 3: 최신본 vs 나머지 전부 포함 관계 검증
        
        Args:
            records: 분석할 FileRecord 리스트
        
        Returns:
            DuplicateGroup 리스트
        """
        if not records:
            return []
        
        # 작은 파일 제외 (< 8KB)
        valid_records = [r for r in records if r.size >= MIN_FILE_SIZE]
        
        if len(valid_records) < 2:
            return []  # 비교할 파일이 부족
        
        self._logger.debug(f"유효 파일: {len(valid_records)}개 (전체 {len(records)}개 중)")
        self._update_progress(f"유효 파일 확인: {len(valid_records)}개")
        
        # Phase 1: 그룹핑
        self._update_progress("Phase 1: 파일 그룹핑 중...")
        groups = self._group_files(valid_records)
        self._update_progress(f"그룹핑 완료: {len(groups)}개 그룹 생성")
        
        # Phase 2 & 3: 각 그룹에서 최신본 선택 및 포함 관계 검증
        self._update_progress("Phase 2-3: 최신본 선택 및 포함 관계 검증 중...")
        duplicate_groups = []
        total_groups = len(groups)
        for idx, group_members in enumerate(groups, 1):
            if len(group_members) < 2:
                continue
            
            # 최신본 선택
            keep_file = self._select_latest_version(group_members)
            
            # 포함 관계 검증 및 중복 그룹 생성
            if idx % GROUP_PROGRESS_UPDATE_INTERVAL == 0 or idx == total_groups:
                self._update_progress(f"그룹 분석 중: {idx}/{total_groups} ({len(duplicate_groups)}개 중복 그룹 발견)")
            
            group = self._mark_duplicates_with_verification(group_members, keep_file)
            if group and len(group.members) > 1:
                duplicate_groups.append(group)
        
        self._update_progress(f"검증 완료: {len(duplicate_groups)}개 중복 그룹 확인")
        return duplicate_groups
    
    def _group_files(self, records: list[FileRecord]) -> list[list[FileRecord]]:
        """파일을 그룹으로 묶습니다.
        
        base_title이 있으면 base_title로 그룹핑,
        base_title이 없으면 head anchor로 버킷팅합니다.
        앵커 해시 계산은 병렬 처리로 성능을 최적화합니다.
        
        Args:
            records: FileRecord 리스트
        
        Returns:
            그룹 리스트 (각 그룹은 FileRecord 리스트)
        """
        # base_title 기준 그룹핑
        base_title_groups: dict[str, list[FileRecord]] = defaultdict(list)
        no_base_title_records: list[FileRecord] = []
        
        # 앵커 해시가 필요한 레코드만 필터링
        records_needing_hash = [
            (idx, record) for idx, record in enumerate(records)
            if not record.anchor_hashes
        ]
        total_records = len(records)
        records_with_hashes = list(records)  # 원본 복사
        
        # 병렬 처리로 앵커 해시 계산
        if records_needing_hash:
            max_workers = min(os.cpu_count() or 4, len(records_needing_hash), MAX_WORKER_THREADS)
            self._logger.debug(f"병렬 앵커 해시 계산 시작: {len(records_needing_hash)}개 파일, {max_workers}개 스레드")
            
            def _compute_hash_for_record(item: tuple[int, FileRecord]) -> tuple[int, FileRecord, Optional[dict[str, str]]]:
                """레코드의 앵커 해시를 계산하는 헬퍼 함수."""
                idx, record = item
                try:
                    # encoding이 "-"인 경우 기본값 사용 (스캔 단계에서 확정되어야 하지만 안전장치)
                    encoding = record.encoding if record.encoding != ENCODING_NOT_DETECTED else DEFAULT_ENCODING
                    anchor_hashes = compute_anchor_hashes(record.path, encoding)
                    return (idx, record, anchor_hashes)
                except Exception as e:
                    self._logger.warning(f"앵커 해시 계산 실패 (스킵): {record.path} - {e}")
                    return (idx, record, None)
            
            # ThreadPoolExecutor로 병렬 처리
            completed_count = 0
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_record = {
                    executor.submit(_compute_hash_for_record, item): item[0]
                    for item in records_needing_hash
                }
                
                for future in as_completed(future_to_record):
                    try:
                        idx, record, anchor_hashes = future.result()
                        if anchor_hashes:
                            # FileRecord 업데이트
                            records_with_hashes[idx] = record.model_copy(update={"anchor_hashes": anchor_hashes})
                        
                        completed_count += 1
                        # 진행 상황 업데이트 (PROGRESS_UPDATE_INTERVAL개마다 또는 마지막)
                        if completed_count % PROGRESS_UPDATE_INTERVAL == 0 or completed_count == len(records_needing_hash):
                            self._update_progress(
                                f"앵커 해시 계산 중: {completed_count}/{len(records_needing_hash)} "
                                f"(전체 {total_records}개 중)"
                            )
                    except Exception as e:
                        self._logger.error(f"앵커 해시 계산 중 예외 발생: {e}", exc_info=True)
        
        # base_title 기준 그룹핑
        for record in records_with_hashes:
            if record.base_title:
                base_title_groups[record.base_title].append(record)
            else:
                no_base_title_records.append(record)
        
        groups: list[list[FileRecord]] = []
        
        # base_title 그룹 추가
        for base_title, group_records in base_title_groups.items():
            if len(group_records) >= 2:
                groups.append(group_records)
                self._logger.debug(
                    f"base_title 그룹: '{base_title}', {len(group_records)}개 파일"
                )
        
        # base_title 없는 파일들은 head anchor로 버킷팅
        if no_base_title_records:
            head_buckets: dict[str, list[FileRecord]] = defaultdict(list)
            for record in no_base_title_records:
                if record.anchor_hashes:
                    head_hash = record.anchor_hashes.get("head", "")
                    if head_hash:
                        head_buckets[head_hash].append(record)
            
            # 버킷 크기 ≥ 2인 것만 그룹으로 추가
            for head_hash, bucket_records in head_buckets.items():
                if len(bucket_records) >= 2:
                    groups.append(bucket_records)
                    self._logger.debug(
                        f"head anchor 버킷: {len(bucket_records)}개 파일"
                    )
        
        self._logger.debug(f"총 {len(groups)}개 그룹 생성")
        return groups
    
    def _select_latest_version(self, group_members: list[FileRecord]) -> FileRecord:
        """최신본을 선택합니다.
        
        우선순위 (단일 패스로 최적화):
        1. episode_end 최대값
        2. size 최대값
        3. mtime 최신
        4. 파일명 토큰 (통합본/합본/완결/최종 우선)
        
        Args:
            group_members: 같은 작품 묶음의 FileRecord 리스트
        
        Returns:
            최신본 FileRecord
        """
        if not group_members:
            raise ValueError("그룹 멤버가 비어있습니다.")
        
        if len(group_members) == 1:
            return group_members[0]
        
        # 단일 패스로 최적 후보 선택 (key 함수를 사용한 max 연산)
        # 튜플 비교: (episode_end, size, mtime, keyword_score, original_index)
        # None은 비교 시 최소값으로 처리됨
        
        priority_keywords = ["통합본", "합본", "완결", "최종"]
        
        def get_sort_key(record: FileRecord, index: int) -> tuple:
            """정렬 키 함수: 우선순위에 따라 튜플 반환."""
            # episode_end: None이면 -1로 처리 (최소값)
            episode_end = record.episode_end if record.episode_end is not None else -1
            
            # size: 항상 있음
            size = record.size
            
            # mtime: None이면 0.0으로 처리 (최소값)
            mtime = record.mtime if record.mtime is not None else 0.0
            
            # keyword_score: 우선순위 높은 키워드가 앞에 오면 높은 점수
            keyword_score = 0
            for i, keyword in enumerate(priority_keywords):
                if keyword in record.name:
                    keyword_score = len(priority_keywords) - i  # 높은 우선순위 = 높은 점수
                    break
            
            # 원본 인덱스: 동률 시 첫 번째 것을 선택하기 위함 (안정성)
            return (episode_end, size, mtime, keyword_score, index)
        
        # max 함수로 단일 패스로 최적 후보 선택
        best_record, _ = max(
            ((record, idx) for idx, record in enumerate(group_members)),
            key=lambda x: get_sort_key(x[0], x[1])
        )
        
        return best_record
    
    def _verify_inclusion_with_anchors(self, latest: FileRecord, older: FileRecord) -> bool:
        """anchor_hashes를 사용하여 포함 관계를 검증합니다.
        
        검증 규칙:
        1. older.head == latest.head
        2. older.tail == latest.tail OR older.tail == latest.mid
        3. latest.size > older.size
        
        Args:
            latest: 최신본 FileRecord
            older: 구버전 FileRecord
        
        Returns:
            포함 관계가 확인되면 True
        """
        if not latest.anchor_hashes or not older.anchor_hashes:
            return False
        
        latest_head = latest.anchor_hashes.get("head", "")
        latest_mid = latest.anchor_hashes.get("mid", "")
        latest_tail = latest.anchor_hashes.get("tail", "")
        
        older_head = older.anchor_hashes.get("head", "")
        older_tail = older.anchor_hashes.get("tail", "")
        
        # 조건 1: head 일치
        if older_head != latest_head:
            return False
        
        # 조건 2: tail이 latest.tail 또는 latest.mid와 일치
        if older_tail != latest_tail and older_tail != latest_mid:
            return False
        
        # 조건 3: latest.size > older.size
        if latest.size <= older.size:
            return False
        
        return True
    
    def _verify_inclusion_fast(
        self, 
        latest_hashes: dict[str, str], 
        latest_size: int,
        older_hashes: dict[str, str],
        older_size: int
    ) -> bool:
        """포함 관계를 빠르게 검증합니다 (해시 딕셔너리만 사용).
        
        O(k²) → O(k) 최적화를 위해 keep_file의 해시를 미리 추출하여 사용.
        
        Args:
            latest_hashes: 최신본의 anchor_hashes 딕셔너리
            latest_size: 최신본 파일 크기
            older_hashes: 구버전의 anchor_hashes 딕셔너리
            older_size: 구버전 파일 크기
        
        Returns:
            포함 관계가 확인되면 True
        """
        if not latest_hashes or not older_hashes:
            return False
        
        latest_head = latest_hashes.get("head", "")
        latest_mid = latest_hashes.get("mid", "")
        latest_tail = latest_hashes.get("tail", "")
        
        older_head = older_hashes.get("head", "")
        older_tail = older_hashes.get("tail", "")
        
        # 조건 1: head 일치
        if older_head != latest_head:
            return False
        
        # 조건 2: tail이 latest.tail 또는 latest.mid와 일치
        if older_tail != latest_tail and older_tail != latest_mid:
            return False
        
        # 조건 3: latest.size > older.size
        if latest_size <= older_size:
            return False
        
        return True
    
    def _verify_inclusion_fallback(self, latest: FileRecord, older: FileRecord) -> bool:
        """포함 관계 검증 폴백 (anchor 검증 실패 시).
        
        폴백 규칙:
        1. episode_end 둘 다 있으면: latest.episode_end > older.episode_end
        2. 아니면: latest.size > older.size * 1.1 (10% 이상 차이)
        
        Args:
            latest: 최신본 FileRecord
            older: 구버전 FileRecord
        
        Returns:
            포함 관계가 확인되면 True
        """
        # 폴백 1: episode_end 비교
        if latest.episode_end is not None and older.episode_end is not None:
            if latest.episode_end > older.episode_end:
                return True
        
        # 폴백 2: size 비교 (10% 이상 차이)
        if latest.size > older.size * SIZE_DIFFERENCE_THRESHOLD:
            return True
        
        return False
    
    def _mark_duplicates_with_verification(
        self, 
        group_members: list[FileRecord], 
        keep_file: FileRecord
    ) -> Optional[DuplicateGroup]:
        """포함 관계 검증을 수행하고 중복 그룹을 생성합니다.
        
        최신본(keep_file)과 나머지 파일들 간의 포함 관계를 검증하여
        중복으로 확인된 파일들만 그룹에 포함시킵니다.
        
        Args:
            group_members: 같은 작품 묶음의 FileRecord 리스트
            keep_file: 유지할 최신본 FileRecord
        
        Returns:
            DuplicateGroup 객체 (중복이 없으면 None)
        """
        # keep_file이 그룹에 포함되어 있는지 확인
        if keep_file not in group_members:
            keep_file = group_members[0]
        
        # 최적화: keep_file의 해시와 크기를 미리 추출 (O(k²) → O(k) 개선)
        keep_hashes = keep_file.anchor_hashes
        keep_size = keep_file.size
        
        # 중복 파일 리스트 (검증 통과한 것만)
        verified_duplicates: list[FileRecord] = []
        verification_evidence: list[dict[str, Any]] = []
        
        for candidate in group_members:
            if candidate == keep_file:
                continue
            
            # 포함 관계 검증
            is_included = False
            verification_method = None
            
            # 1순위: anchor 검증 (최적화된 빠른 검증 사용)
            if (keep_hashes and candidate.anchor_hashes and 
                self._verify_inclusion_fast(
                    keep_hashes, keep_size,
                    candidate.anchor_hashes, candidate.size
                )):
                is_included = True
                verification_method = "anchor_hashes"
            # 2순위: 폴백 검증
            elif self._verify_inclusion_fallback(keep_file, candidate):
                is_included = True
                verification_method = "fallback"
            
            if is_included:
                verified_duplicates.append(candidate)
                verification_evidence.append({
                    "file": str(candidate.path),
                    "method": verification_method
                })
        
        # 중복이 없으면 None 반환
        if not verified_duplicates:
            return None
        
        # 중복 강도 결정
        duplicate_strength = "STRONG" if any(
            ev.get("method") == "anchor_hashes" for ev in verification_evidence
        ) else "WEAK"
        
        # 판정 근거
        reason = "LATEST_INCLUDES_OLDER"
        evidence = {
            "keep_file": str(keep_file.path),
            "duplicate_count": len(verified_duplicates),
            "base_title": keep_file.base_title,
            "episode_end": keep_file.episode_end,
            "selection_rule": "episode_end_max" if keep_file.episode_end else "size_max",
            "verification_details": verification_evidence
        }
        
        # confidence 계산
        confidence = CONFIDENCE_STRONG if duplicate_strength == "STRONG" else CONFIDENCE_WEAK
        
        # 그룹 생성 (keep_file + verified_duplicates)
        group = DuplicateGroup(
            members=[keep_file] + verified_duplicates,
            reason=reason,
            evidence=evidence,
            confidence=confidence,
            keep_file=keep_file,
            duplicate_strength=duplicate_strength
        )
        
        self._logger.debug(
            f"중복 그룹 생성: keep={keep_file.name}, "
            f"duplicates={len(verified_duplicates)}개, strength={duplicate_strength}"
        )
        
        return group
