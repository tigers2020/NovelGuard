"""
포함 관계 검증 모듈

최신본과 구버전 간의 포함 관계를 검증하는 기능을 제공합니다.
"""

import re
from models.file_record import FileRecord
from utils.logger import get_logger
from utils.constants import SIZE_DIFFERENCE_THRESHOLD

# 권수/부수 추출 패턴
_VOLUME_PATTERN = re.compile(r'(\d+)권', re.IGNORECASE)
_PART_PATTERN = re.compile(r'(\d+)부', re.IGNORECASE)


class InclusionVerifier:
    """포함 관계 검증 클래스.
    
    최신본이 구버전을 포함하는지 검증합니다.
    anchor_hashes 기반 검증을 우선 사용하고, 실패 시 폴백 검증을 수행합니다.
    """
    
    def __init__(self) -> None:
        """InclusionVerifier 초기화."""
        self._logger = get_logger("InclusionVerifier")
    
    def verify(self, latest: FileRecord, older: FileRecord) -> tuple[bool, str]:
        """포함 관계를 검증합니다.
        
        검증 순서:
        1. episode_range가 겹치지 않으면 중복이 아님 (연속 권수/회차 체크)
        2. anchor_hashes 기반 검증 (우선)
        3. 폴백 검증 (episode_end 또는 size 비교)
        
        Args:
            latest: 최신본 FileRecord
            older: 구버전 FileRecord
        
        Returns:
            (검증 결과, 검증 방법) 튜플
            - 검증 결과: True이면 포함 관계 확인, False이면 미확인
            - 검증 방법: "anchor_hashes", "fallback", 또는 "none"
        """
        # 0순위: episode_range가 겹치지 않으면 중복이 아님 (연속 권수/회차 체크)
        if self._are_ranges_disjoint(latest, older):
            self._logger.debug(
                f"episode_range가 겹치지 않음: latest={latest.episode_range}, "
                f"older={older.episode_range} → 중복 아님"
            )
            return (False, "none")
        
        # 1순위: anchor 검증 (최적화된 빠른 검증 사용)
        if latest.anchor_hashes and older.anchor_hashes:
            if self._verify_with_anchors_fast(
                latest.anchor_hashes, latest.size,
                older.anchor_hashes, older.size
            ):
                return (True, "anchor_hashes")
        
        # 2순위: 폴백 검증
        if self._verify_fallback(latest, older):
            return (True, "fallback")
        
        return (False, "none")
    
    def verify_with_anchors(self, latest: FileRecord, older: FileRecord) -> bool:
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
    
    def _verify_with_anchors_fast(
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
    
    def _are_ranges_disjoint(self, latest: FileRecord, older: FileRecord) -> bool:
        """episode_range 또는 권수/부수가 겹치지 않는지 확인합니다.
        
        연속된 권수/회차는 중복이 아니므로, 범위가 겹치지 않으면 중복이 아닙니다.
        
        Args:
            latest: 최신본 FileRecord
            older: 구버전 FileRecord
        
        Returns:
            범위가 겹치지 않으면 True (중복 아님), 겹치거나 둘 중 하나가 None이면 False
        """
        # 1. episode_range 비교
        if latest.episode_range and older.episode_range:
            latest_start, latest_end = latest.episode_range
            older_start, older_end = older.episode_range
            
            # 범위가 겹치지 않는 경우: latest가 older보다 완전히 뒤에 있거나, older가 latest보다 완전히 뒤에 있음
            # latest: [1, 10], older: [11, 20] → 겹치지 않음
            # latest: [11, 20], older: [1, 10] → 겹치지 않음
            # latest: [1, 20], older: [10, 30] → 겹침 (중복 가능)
            if latest_end < older_start or older_end < latest_start:
                return True
        
        # 2. episode_range가 없으면 파일명에서 권수/부수 추출하여 비교
        if not latest.episode_range and not older.episode_range:
            latest_info = self._extract_volume_or_part(latest.name)
            older_info = self._extract_volume_or_part(older.name)
            
            # 둘 다 권수/부수 정보가 있으면 비교
            if latest_info is not None and older_info is not None:
                latest_volume, latest_part = latest_info
                older_volume, older_part = older_info
                
                # 권수나 부수가 다르면 중복이 아님 (연속된 권수/다른 부수)
                if latest_volume != older_volume or latest_part != older_part:
                    return True
        
        # 범위가 겹치거나 포함 관계, 또는 비교 불가
        return False
    
    def _extract_volume_or_part(self, filename: str) -> Optional[tuple[int, Optional[int]]]:
        """파일명에서 권수와 부수를 추출합니다.
        
        Args:
            filename: 파일명
        
        Returns:
            (권수, 부수) 튜플. 권수가 없으면 (None, 부수). 둘 다 없으면 None.
        """
        if not filename:
            return None
        
        # 확장자 제거
        name = filename.rsplit('.', 1)[0] if '.' in filename else filename
        
        # 권수 추출 (예: "01권", "1권")
        volume = None
        match = _VOLUME_PATTERN.search(name)
        if match:
            try:
                volume = int(match.group(1))
            except (ValueError, IndexError):
                pass
        
        # 부수 추출 (예: "1부", "2부")
        part = None
        match = _PART_PATTERN.search(name)
        if match:
            try:
                part = int(match.group(1))
            except (ValueError, IndexError):
                pass
        
        # 권수와 부수를 함께 반환 (둘 다 없으면 None)
        if volume is None and part is None:
            return None
        
        return (volume, part)
    
    def _verify_fallback(self, latest: FileRecord, older: FileRecord) -> bool:
        """포함 관계 검증 폴백 (anchor 검증 실패 시).
        
        폴백 규칙:
        1. episode_end 둘 다 있으면: latest.episode_end > older.episode_end
           (단, episode_range가 겹치는 경우에만)
        2. 아니면: latest.size > older.size * 1.1 (10% 이상 차이)
        
        Args:
            latest: 최신본 FileRecord
            older: 구버전 FileRecord
        
        Returns:
            포함 관계가 확인되면 True
        """
        # 폴백 1: episode_end 비교 (episode_range가 겹치는 경우에만)
        if latest.episode_end is not None and older.episode_end is not None:
            # episode_range가 겹치거나 포함 관계인 경우에만 중복 가능
            if not self._are_ranges_disjoint(latest, older):
                if latest.episode_end > older.episode_end:
                    return True
        
        # 폴백 2: size 비교 (10% 이상 차이)
        if latest.size > older.size * SIZE_DIFFERENCE_THRESHOLD:
            return True
        
        return False

