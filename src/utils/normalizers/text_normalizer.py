"""
본문 정규화 모듈

본문 텍스트를 정규화하는 기능을 제공합니다.
"""

import re

# 정규화 성능 최적화를 위한 컴파일된 정규식
_WHITESPACE_PATTERN = re.compile(r'[ \t]+')
_CRLF_PATTERN = re.compile(r'\r\n?')
_ZERO_WIDTH_CHARS = str.maketrans('', '', '\u200b\u200c\u200d\ufeff')


class TextNormalizer:
    """본문 정규화 클래스.
    
    본문 텍스트를 정규화하여 비교에 사용합니다.
    공백과 줄바꿈을 정규화합니다.
    """
    
    def normalize(self, content: str) -> str:
        """본문 비교용 텍스트 정규화.
        
        공백/줄바꿈 차이만 있는 파일도 동일하게 인식하기 위한 정규화.
        v1.5 normalized_hash에서도 사용됩니다.
        성능 최적화: 컴파일된 정규식과 translate를 사용하여 처리 속도 향상.
        
        Args:
            content: 원본 텍스트 내용
        
        Returns:
            정규화된 텍스트
        
        Example:
            >>> normalizer = TextNormalizer()
            >>> text1 = "안녕하세요\\r\\n반갑습니다  "
            >>> text2 = "안녕하세요\\n반갑습니다"
            >>> normalizer.normalize(text1) == normalizer.normalize(text2)
            True
        """
        if not content:
            return ""
        
        # 1. 줄바꿈 통일 (CRLF/LF/CR → LF) - 컴파일된 정규식 사용
        normalized = _CRLF_PATTERN.sub('\n', content)
        
        # 2. 연속 공백 축약 (탭 포함) - 컴파일된 정규식 사용
        # 단, 줄바꿈은 유지
        lines = normalized.split('\n')
        normalized_lines = []
        for line in lines:
            # 줄 내 연속 공백을 단일 공백으로
            normalized_line = _WHITESPACE_PATTERN.sub(' ', line)
            normalized_lines.append(normalized_line)
        normalized = '\n'.join(normalized_lines)
        
        # 3. 제로폭 문자 제거 - translate 사용 (한 번에 처리)
        normalized = normalized.translate(_ZERO_WIDTH_CHARS)
        
        # 4. 앞뒤 공백 제거
        normalized = normalized.strip()
        
        return normalized

