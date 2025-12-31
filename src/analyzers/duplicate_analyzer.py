"""
중복 파일 분석 모듈

파일 중복을 탐지하고 분석하는 기능을 제공합니다.
최신본 기준 중복 판별기: base_title 그룹핑 → 최신본 선택 → 포함 관계 검증 파이프라인.
"""

from typing import Optional, Any, Callable

from models.file_record import FileRecord
from utils.logger import get_logger
from utils.exceptions import DuplicateAnalysisError
from utils.constants import (
    MIN_FILE_SIZE,
    GROUP_PROGRESS_UPDATE_INTERVAL,
    CONFIDENCE_STRONG,
    CONFIDENCE_WEAK,
)
from analyzers.duplicate_group import DuplicateGroup
from analyzers.file_grouper import FileGrouper
from analyzers.latest_version_selector import LatestVersionSelector
from analyzers.inclusion_verifier import InclusionVerifier
from analyzers.duplicate_group_builder import DuplicateGroupBuilder


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
        
        # 분리된 책임 클래스들 초기화
        self._grouper = FileGrouper(progress_callback=progress_callback)
        self._selector = LatestVersionSelector()
        self._verifier = InclusionVerifier()
        self._group_builder = DuplicateGroupBuilder()
    
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
        groups = self._grouper.group_files(valid_records)
        self._update_progress(f"그룹핑 완료: {len(groups)}개 그룹 생성")
        
        # Phase 2 & 3: 각 그룹에서 최신본 선택 및 포함 관계 검증
        self._update_progress("Phase 2-3: 최신본 선택 및 포함 관계 검증 중...")
        duplicate_groups = []
        total_groups = len(groups)
        for idx, group_members in enumerate(groups, 1):
            if len(group_members) < 2:
                continue
            
            # 최신본 선택
            keep_file = self._selector.select_latest(group_members)
            
            # 포함 관계 검증 및 중복 그룹 생성
            if idx % GROUP_PROGRESS_UPDATE_INTERVAL == 0 or idx == total_groups:
                self._update_progress(f"그룹 분석 중: {idx}/{total_groups} ({len(duplicate_groups)}개 중복 그룹 발견)")
            
            group = self._mark_duplicates_with_verification(group_members, keep_file)
            if group and len(group.members) > 1:
                duplicate_groups.append(group)
        
        self._update_progress(f"검증 완료: {len(duplicate_groups)}개 중복 그룹 확인")
        return duplicate_groups
    
    
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
        
        # 중복 파일 리스트 (검증 통과한 것만)
        verified_duplicates: list[FileRecord] = []
        verification_evidence: list[dict[str, Any]] = []
        
        for candidate in group_members:
            if candidate == keep_file:
                continue
            
            # 포함 관계 검증
            is_included, verification_method = self._verifier.verify(keep_file, candidate)
            
            if is_included:
                verified_duplicates.append(candidate)
                verification_evidence.append({
                    "file": str(candidate.path),
                    "method": verification_method
                })
        
        # 중복 그룹 생성 (DuplicateGroupBuilder 사용)
        return self._group_builder.build(keep_file, verified_duplicates, verification_evidence)
