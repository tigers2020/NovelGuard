"""
제목 추출기 모듈

파일명에서 제목을 추출하는 기능을 제공합니다.
"""

import re
from typing import Optional

# 성능 최적화: 정규식 패턴을 모듈 레벨에서 컴파일하여 캐싱
_TITLE_PATTERNS = [
    re.compile(r'\s+\d+[-~]\d+', re.IGNORECASE),  # "1-114", "1~158"
    re.compile(r'\s+\d+[-~]\d+화', re.IGNORECASE),  # "1-50화"
    re.compile(r'\s+\d+권', re.IGNORECASE),  # "01권", "1권"
    re.compile(r'\s+제\d+권', re.IGNORECASE),  # "제1권"
    re.compile(r'\s+Chapter\s+\d+', re.IGNORECASE),  # "Chapter 1"
    re.compile(r'\s+Ch\.\s*\d+', re.IGNORECASE),  # "Ch. 1"
    re.compile(r'\s+Ep\.\s*\d+', re.IGNORECASE),  # "Ep. 1"
    re.compile(r'\s+\d+부', re.IGNORECASE),  # "1부"
]


class TitleExtractor:
    """제목 추출기 클래스.
    
    파일명에서 제목을 추출합니다.
    패턴: "제목 + 공백 + 숫자/회차 정보"
    """
    
    def extract(self, filename: str) -> str:
        """파일명에서 제목을 추출합니다 (원본).
        
        Args:
            filename: 파일명 (확장자 포함 가능)
        
        Returns:
            추출된 제목 (원본). 파싱 실패 시 전체 파일명 반환.
        
        Example:
            >>> extractor = TitleExtractor()
            >>> extractor.extract("게임 속 최종보스가 되었다 1-114.txt")
            "게임 속 최종보스가 되었다"
            >>> extractor.extract("갓 오브 블랙필드 1부 01권.txt")
            "갓 오브 블랙필드 1부"
        """
        if not filename:
            return ""
        
        # 확장자 제거
        name = filename.rsplit('.', 1)[0] if '.' in filename else filename
        
        # 가장 먼저 매칭되는 패턴으로 제목 추출 (컴파일된 정규식 사용)
        for pattern in _TITLE_PATTERNS:
            match = pattern.search(name)
            if match:
                # 패턴 앞부분이 제목
                title = name[:match.start()].strip()
                if title:
                    return title
        
        # 패턴 매칭 실패 시 전체 이름 반환
        return name.strip()
    
    def extract_normalized(self, filename: str) -> str:
        """파일명에서 정규화된 제목을 추출합니다.
        
        extract() + normalize_title() 조합.
        그룹핑에 사용됩니다.
        
        Args:
            filename: 파일명 (확장자 포함 가능)
        
        Returns:
            정규화된 제목
        
        Example:
            >>> extractor = TitleExtractor()
            >>> extractor.extract_normalized("게임 속 최종보스가 되었다 (완결) 1-114.txt")
            "게임 속 최종보스가 되었다"
        """
        from utils.text_normalizer import normalize_title
        title = self.extract(filename)
        return normalize_title(title)

