"""
최신본 선택 모듈

그룹 내에서 최신본을 선택하는 로직을 제공합니다.
"""

from models.file_record import FileRecord
from utils.logger import get_logger


class LatestVersionSelector:
    """최신본 선택 클래스.
    
    그룹 내에서 최신본을 선택합니다.
    우선순위: episode_end 최대값 → size 최대값 → mtime 최신 → 파일명 키워드
    """
    
    def __init__(self) -> None:
        """LatestVersionSelector 초기화."""
        self._logger = get_logger("LatestVersionSelector")
    
    def select_latest(self, group_members: list[FileRecord]) -> FileRecord:
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
        
        Raises:
            ValueError: 그룹 멤버가 비어있을 때
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

