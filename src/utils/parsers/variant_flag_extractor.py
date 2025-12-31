"""
변형 플래그 추출기 모듈

파일명에서 변형 플래그를 추출하는 기능을 제공합니다.
"""

import re
from typing import Optional

# extract_variant_flags에서 사용하는 키워드
_VARIANT_KEYWORDS = [
    "외전", "번외", "특별편", "특전", "완결", "정발", "번역", 
    "수정", "합본", "통합본", "통합", "합치기", "단행본",
    "1부", "2부", "3부", "4부", "5부", "상", "하", "전편", "후편"
]


class VariantFlagExtractor:
    """변형 플래그 추출기 클래스.
    
    파일명에서 변형 플래그를 추출합니다.
    외전/번외/특별편/완결/합본 등의 플래그를 추출합니다.
    """
    
    def extract(self, filename: str) -> list[str]:
        """파일명에서 변형 플래그를 추출합니다.
        
        외전/번외/특별편/완결/합본 등의 플래그를 추출합니다.
        
        Args:
            filename: 파일명 (확장자 포함 가능)
        
        Returns:
            변형 플래그 리스트
        
        Example:
            >>> extractor = VariantFlagExtractor()
            >>> extractor.extract("게임 속 최종보스가 되었다 외전 1-10.txt")
            ["외전"]
            >>> extractor.extract("갓 오브 블랙필드 완결 합본.txt")
            ["완결", "합본"]
        """
        if not filename:
            return []
        
        # 확장자 제거
        name = filename.rsplit('.', 1)[0] if '.' in filename else filename
        
        flags = []
        for keyword in _VARIANT_KEYWORDS:
            # 단어 경계를 고려한 검색 (정규식은 매번 컴파일되지만 키워드 수가 적어 성능 영향 미미)
            # 필요시 모듈 레벨에서 컴파일된 패턴 리스트로 최적화 가능
            pattern = rf'\b{re.escape(keyword)}\b'
            if re.search(pattern, name, re.IGNORECASE):
                flags.append(keyword)
        
        return flags

