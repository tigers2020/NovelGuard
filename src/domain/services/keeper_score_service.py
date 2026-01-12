"""Keeper 점수화 서비스."""
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from app.settings.constants import Constants
from domain.entities.file_entry import FileEntry
from domain.value_objects.filename_parse_result import FilenameParseResult

if TYPE_CHECKING:
    from application.ports.log_sink import ILogSink


class KeeperScoreService:
    """Keeper 점수화 서비스.
    
    중복 그룹에서 keeper(유지할 파일)를 추천하기 위한 점수 계산 서비스.
    단일 규칙 기반 추천보다 점수화 방식이 오탐 위험이 낮음.
    
    점수 체계 상수는 Constants 클래스에서 관리합니다.
    """
    
    def __init__(self, log_sink: Optional["ILogSink"] = None) -> None:
        """KeeperScoreService 초기화.
        
        Args:
            log_sink: 로그 싱크 (선택적, 디버깅 목적).
        """
        self._log_sink = log_sink
    
    def calculate_keeper_score(
        self,
        file_entry: FileEntry,
        parse_result: FilenameParseResult,
        reference_mtime: Optional[datetime] = None
    ) -> int:
        """Keeper 점수 계산.
        
        Args:
            file_entry: 파일 엔트리.
            parse_result: 파일명 파싱 결과.
            reference_mtime: 기준 수정 시간 (None이면 file_entry.mtime 사용).
        
        Returns:
            Keeper 점수 (높을수록 keeper로 추천).
        """
        score = 0
        
        # +100: 완결 태그 포함
        if parse_result.is_complete:
            score += Constants.SCORE_COMPLETE_TAG
        
        # +50: coverage 큰 쪽 (segments 기준 또는 primary range_end)
        if parse_result.has_segments:
            coverage = parse_result.total_coverage
            score += int(coverage * Constants.SCORE_COVERAGE / 100)
        elif parse_result.has_range:
            coverage = parse_result.range_end - parse_result.range_start + 1
            score += int(coverage * Constants.SCORE_COVERAGE / 100)
        
        # +20: mtime 최신 (reference_mtime 기준)
        if reference_mtime is None:
            reference_mtime = file_entry.mtime
        
        # 가장 최신 파일에 점수 부여 (상대적 비교는 select_keeper에서)
        # 여기서는 절대 점수만 계산하므로 mtime 점수는 select_keeper에서 처리
        
        # +10: size 큰 쪽 (상대적 비교는 select_keeper에서)
        # 여기서는 절대 점수만 계산하므로 size 점수는 select_keeper에서 처리
        
        # -1000: 파싱 신뢰도 낮음
        if parse_result.confidence < Constants.CONFIDENCE_THRESHOLD:
            score += Constants.PENALTY_LOW_CONFIDENCE
        
        return score
    
    def select_keeper(
        self,
        files_with_parse: list[tuple[FileEntry, FilenameParseResult]]
    ) -> Optional[FileEntry]:
        """Keeper 선택.
        
        Args:
            files_with_parse: (FileEntry, FilenameParseResult) 튜플 리스트.
        
        Returns:
            추천 keeper 파일. 없으면 None.
        """
        if not files_with_parse:
            return None
        
        if len(files_with_parse) == 1:
            return files_with_parse[0][0]
        
        # 가장 최신 mtime 찾기 (상대 비교용)
        max_mtime = max(file_entry.mtime for file_entry, _ in files_with_parse)
        
        # 가장 큰 size 찾기 (상대 비교용)
        max_size = max(file_entry.size for file_entry, _ in files_with_parse)
        
        # 각 파일의 점수 계산
        scored_files = []
        for file_entry, parse_result in files_with_parse:
            base_score = self.calculate_keeper_score(file_entry, parse_result, max_mtime)
            
            # 상대적 점수 추가
            # +20: mtime 최신 (가장 최신 파일에만)
            if file_entry.mtime == max_mtime:
                base_score += Constants.SCORE_MTIME
            
            # +10: size 큰 쪽 (가장 큰 파일에만)
            if file_entry.size == max_size:
                base_score += Constants.SCORE_SIZE
            
            scored_files.append((file_entry, base_score))
        
        # 점수 기준 정렬 (내림차순)
        scored_files.sort(key=lambda x: x[1], reverse=True)
        
        # 최고 점수 파일 반환
        keeper = scored_files[0][0]
        
        return keeper
    
    def select_keeper_id(
        self,
        files_with_parse: list[tuple[FileEntry, FilenameParseResult]]
    ) -> Optional[int]:
        """Keeper ID 선택.
        
        Args:
            files_with_parse: (FileEntry, FilenameParseResult) 튜플 리스트.
        
        Returns:
            추천 keeper 파일 ID. 없으면 None.
        """
        keeper = self.select_keeper(files_with_parse)
        if keeper is None:
            return None
        
        if keeper.file_id is not None:
            return keeper.file_id
        
        # file_id가 없으면 path 기반 해시 사용 (하위 호환성)
        return hash(str(keeper.path))
