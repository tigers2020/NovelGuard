"""
제목 정규화 모듈

제목을 정규화하는 기능을 제공합니다.
"""

import re
from typing import Set

# 꼬리표 제거용 키워드 집합
TAIL_TAGS: Set[str] = {
    "완결", "외전", "번역", "수정", "합본", "통합", "합치기", 
    "단행본", "웹", "EPUB에서 변환", "EPUB", "변환",
    "수정본", "최종", "최종본", "완전판", "완전판본"
}


class TitleNormalizer:
    """제목 정규화 클래스.
    
    제목을 정규화하여 그룹핑에 사용합니다.
    괄호/대괄호 내용과 꼬리표를 제거합니다.
    """
    
    def normalize(self, title: str) -> str:
        """제목을 정규화합니다.
        
        그룹핑 품질 향상을 위해 제목의 변형을 통일합니다.
        
        Args:
            title: 정규화할 제목
        
        Returns:
            정규화된 제목
        
        Example:
            >>> normalizer = TitleNormalizer()
            >>> normalizer.normalize("게임 속 최종보스가 되었다 (완결)")
            "게임 속 최종보스가 되었다"
            >>> normalizer.normalize("갓 오브 블랙필드 1부 01권")
            "갓 오브 블랙필드 1부"
        """
        if not title:
            return ""
        
        # 1. 연속 공백을 단일 공백으로
        normalized = re.sub(r'\s+', ' ', title)
        
        # 2. 괄호 내용 제거 (선택적 - 외전, 번역 등 표기 제거)
        # 예: "제목 (완결)" -> "제목"
        normalized = re.sub(r'\s*\([^)]*\)', '', normalized)
        normalized = re.sub(r'\s*\[[^\]]*\]', '', normalized)
        
        # 3. 꼬리표 제거
        for tag in TAIL_TAGS:
            # 단어 경계를 고려한 제거
            pattern = rf'\b{re.escape(tag)}\b'
            normalized = re.sub(pattern, '', normalized, flags=re.IGNORECASE)
        
        # 4. 제로폭 문자 제거
        normalized = normalized.replace('\u200b', '')  # Zero-width space
        normalized = normalized.replace('\u200c', '')  # Zero-width non-joiner
        normalized = normalized.replace('\u200d', '')  # Zero-width joiner
        normalized = normalized.replace('\ufeff', '')  # Zero-width no-break space
        
        # 5. 앞뒤 공백 제거
        normalized = normalized.strip()
        
        # 6. 연속 공백 다시 정리 (꼬리표 제거 후 생긴 공백)
        normalized = re.sub(r'\s+', ' ', normalized)
        
        return normalized.strip()

