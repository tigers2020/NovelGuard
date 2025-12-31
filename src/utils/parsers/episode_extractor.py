"""
회차 추출기 모듈

파일명에서 회차 관련 정보를 추출하는 기능을 제공합니다.
"""

import re
from typing import Optional

# 성능 최적화: 정규식 패턴을 모듈 레벨에서 컴파일하여 캐싱
_EPISODE_RANGE_PATTERN = re.compile(r'(\d+)[-~](\d+)화?')

# extract_base_title에서 사용하는 패턴들
_EPISODE_PATTERNS = [
    re.compile(r'\s+\d+[-~]\d+화?', re.IGNORECASE),  # "1-114", "1~158", "1-50화"
    re.compile(r'\s+\d{3,}[-~]\d{3,}', re.IGNORECASE),  # "001-009"
]

_VOLUME_PATTERNS = [
    re.compile(r'\s+\d+권', re.IGNORECASE),  # "01권", "1권"
    re.compile(r'\s+제\d+권', re.IGNORECASE),  # "제1권"
    re.compile(r'\s+\d+부', re.IGNORECASE),  # "1부", "2부"
    re.compile(r'\s+Chapter\s+\d+', re.IGNORECASE),  # "Chapter 1"
    re.compile(r'\s+Ch\.\s*\d+', re.IGNORECASE),  # "Ch. 1"
    re.compile(r'\s+Ep\.\s*\d+', re.IGNORECASE),  # "Ep. 1"
]


class EpisodeExtractor:
    """회차 추출기 클래스.
    
    파일명에서 회차 범위, episode_end, base_title을 추출합니다.
    """
    
    def extract_range(self, filename: str) -> Optional[tuple[int, int]]:
        """파일명에서 회차 범위를 추출합니다.
        
        Args:
            filename: 파일명 (확장자 포함 가능)
        
        Returns:
            (시작회차, 끝회차) 튜플. 파싱 실패 시 None.
        
        Example:
            >>> extractor = EpisodeExtractor()
            >>> extractor.extract_range("게임 속 최종보스가 되었다 1-114.txt")
            (1, 114)
            >>> extractor.extract_range("갓 오브 블랙필드 1부 01권.txt")
            None
        """
        if not filename:
            return None
        
        # 확장자 제거
        name = filename.rsplit('.', 1)[0] if '.' in filename else filename
        
        # 회차 범위 패턴 매칭 (컴파일된 정규식 사용)
        match = _EPISODE_RANGE_PATTERN.search(name)
        if match:
            try:
                start = int(match.group(1))
                end = int(match.group(2))
                if start > 0 and end > 0 and start <= end:
                    return (start, end)
            except (ValueError, IndexError):
                pass
        
        # 패턴 매칭 실패
        return None
    
    def extract_end(self, filename: str) -> Optional[int]:
        """파일명에서 회차 범위의 끝값을 추출합니다.
        
        Args:
            filename: 파일명 (확장자 포함 가능)
        
        Returns:
            episode_end (회차 범위의 끝값). 파싱 실패 시 None.
        
        Example:
            >>> extractor = EpisodeExtractor()
            >>> extractor.extract_end("게임 속 최종보스가 되었다 1-114.txt")
            114
            >>> extractor.extract_end("갓 오브 블랙필드 1부 01권.txt")
            None
        """
        episode_range = self.extract_range(filename)
        if episode_range:
            return episode_range[1]  # (start, end) 튜플에서 end 반환
        return None
    
    def extract_base_title(self, filename: str) -> str:
        """파일명에서 base_title을 추출합니다 (에피소드/권수/파트 제거).
        
        작품명만 남기고 에피소드 범위, 권수, 파트, 변형 토큰을 모두 제거합니다.
        
        Args:
            filename: 파일명 (확장자 포함 가능)
        
        Returns:
            base_title (정규화된 작품명)
        
        Example:
            >>> extractor = EpisodeExtractor()
            >>> extractor.extract_base_title("게임 속 최종보스가 되었다 1-114.txt")
            "게임 속 최종보스가 되었다"
            >>> extractor.extract_base_title("갓 오브 블랙필드 외전 001-009.txt")
            "갓 오브 블랙필드"
        """
        if not filename:
            return ""
        
        # 확장자 제거
        name = filename.rsplit('.', 1)[0] if '.' in filename else filename
        
        # 1. 에피소드 범위 패턴 제거 (컴파일된 정규식 사용)
        for pattern in _EPISODE_PATTERNS:
            name = pattern.sub('', name)
        
        # 2. 권수/파트 패턴 제거 (컴파일된 정규식 사용)
        for pattern in _VOLUME_PATTERNS:
            name = pattern.sub('', name)
        
        # 3. 제목 추출 (남은 부분에서)
        title = name.strip()
        
        # 4. normalize_title 적용 (괄호/대괄호, 변형 토큰 제거)
        from utils.text_normalizer import normalize_title
        base_title = normalize_title(title)
        
        return base_title

