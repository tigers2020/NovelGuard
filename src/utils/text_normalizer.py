"""
텍스트 정규화 유틸리티

파일명과 본문 텍스트를 정규화하는 기능을 제공합니다.
정규화 규칙을 한 곳에 모아 재사용 가능하게 구성합니다.
"""

import re
from typing import Set

# 정규화 성능 최적화를 위한 컴파일된 정규식
_WHITESPACE_PATTERN = re.compile(r'[ \t]+')
_CRLF_PATTERN = re.compile(r'\r\n?')
_ZERO_WIDTH_CHARS = str.maketrans('', '', '\u200b\u200c\u200d\ufeff')


# 꼬리표 제거용 키워드 집합
TAIL_TAGS: Set[str] = {
    "완결", "외전", "번역", "수정", "합본", "통합", "합치기", 
    "단행본", "웹", "EPUB에서 변환", "EPUB", "변환",
    "수정본", "최종", "최종본", "완전판", "완전판본"
}


def normalize_title(title: str) -> str:
    """제목을 정규화합니다.
    
    그룹핑 품질 향상을 위해 제목의 변형을 통일합니다.
    
    Args:
        title: 원본 제목 문자열
    
    Returns:
        정규화된 제목 문자열
    
    Example:
        >>> normalize_title("게임 속 최종보스가 되었다 (완결)")
        "게임 속 최종보스가 되었다"
        >>> normalize_title("갓 오브 블랙필드 1부 01권")
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


def normalize_text_for_comparison(content: str) -> str:
    """본문 비교용 텍스트 정규화.
    
    공백/줄바꿈 차이만 있는 파일도 동일하게 인식하기 위한 정규화.
    v1.5 normalized_hash에서도 사용됩니다.
    성능 최적화: 컴파일된 정규식과 translate를 사용하여 처리 속도 향상.
    
    Args:
        content: 원본 텍스트 내용
    
    Returns:
        정규화된 텍스트
    
    Example:
        >>> text1 = "안녕하세요\\r\\n반갑습니다  "
        >>> text2 = "안녕하세요\\n반갑습니다"
        >>> normalize_text_for_comparison(text1) == normalize_text_for_comparison(text2)
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

