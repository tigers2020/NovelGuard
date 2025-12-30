"""
파일명 파싱 유틸리티

파일명에서 제목과 회차 범위를 추출하는 기능을 제공합니다.
"""

import re
from typing import Optional

from utils.text_normalizer import normalize_title

# 성능 최적화: 정규식 패턴을 모듈 레벨에서 컴파일하여 캐싱
# extract_title에서 사용하는 패턴들
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

# extract_episode_range에서 사용하는 패턴
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

# extract_variant_flags에서 사용하는 키워드 (정규식은 동적으로 생성)
_VARIANT_KEYWORDS = [
    "외전", "번외", "특별편", "특전", "완결", "정발", "번역", 
    "수정", "합본", "통합본", "통합", "합치기", "단행본",
    "1부", "2부", "3부", "4부", "5부", "상", "하", "전편", "후편"
]


def extract_title(filename: str) -> str:
    """파일명에서 제목을 추출합니다 (원본).
    
    패턴: "제목 + 공백 + 숫자/회차 정보"
    
    Args:
        filename: 파일명 (확장자 포함 가능)
    
    Returns:
        추출된 제목 (원본). 파싱 실패 시 전체 파일명 반환.
    
    Example:
        >>> extract_title("게임 속 최종보스가 되었다 1-114.txt")
        "게임 속 최종보스가 되었다"
        >>> extract_title("갓 오브 블랙필드 1부 01권.txt")
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


def extract_normalized_title(filename: str) -> str:
    """파일명에서 정규화된 제목을 추출합니다.
    
    extract_title() + normalize_title() 조합.
    그룹핑에 사용됩니다.
    
    Args:
        filename: 파일명 (확장자 포함 가능)
    
    Returns:
        정규화된 제목
    
    Example:
        >>> extract_normalized_title("게임 속 최종보스가 되었다 (완결) 1-114.txt")
        "게임 속 최종보스가 되었다"
    """
    title = extract_title(filename)
    return normalize_title(title)


def extract_episode_range(filename: str) -> Optional[tuple[int, int]]:
    """파일명에서 회차 범위를 추출합니다.
    
    Args:
        filename: 파일명 (확장자 포함 가능)
    
    Returns:
        (시작회차, 끝회차) 튜플. 파싱 실패 시 None.
    
    Example:
        >>> extract_episode_range("게임 속 최종보스가 되었다 1-114.txt")
        (1, 114)
        >>> extract_episode_range("갓 오브 블랙필드 1부 01권.txt")
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


def extract_base_title(filename: str) -> str:
    """파일명에서 base_title을 추출합니다 (에피소드/권수/파트 제거).
    
    작품명만 남기고 에피소드 범위, 권수, 파트, 변형 토큰을 모두 제거합니다.
    
    Args:
        filename: 파일명 (확장자 포함 가능)
    
    Returns:
        base_title (정규화된 작품명)
    
    Example:
        >>> extract_base_title("게임 속 최종보스가 되었다 1-114.txt")
        "게임 속 최종보스가 되었다"
        >>> extract_base_title("갓 오브 블랙필드 외전 001-009.txt")
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
    base_title = normalize_title(title)
    
    return base_title


def extract_episode_end(filename: str) -> Optional[int]:
    """파일명에서 회차 범위의 끝값을 추출합니다.
    
    Args:
        filename: 파일명 (확장자 포함 가능)
    
    Returns:
        episode_end (회차 범위의 끝값). 파싱 실패 시 None.
    
    Example:
        >>> extract_episode_end("게임 속 최종보스가 되었다 1-114.txt")
        114
        >>> extract_episode_end("갓 오브 블랙필드 1부 01권.txt")
        None
    """
    episode_range = extract_episode_range(filename)
    if episode_range:
        return episode_range[1]  # (start, end) 튜플에서 end 반환
    return None


def extract_variant_flags(filename: str) -> list[str]:
    """파일명에서 변형 플래그를 추출합니다.
    
    외전/번외/특별편/완결/합본 등의 플래그를 추출합니다.
    
    Args:
        filename: 파일명 (확장자 포함 가능)
    
    Returns:
        변형 플래그 리스트
    
    Example:
        >>> extract_variant_flags("게임 속 최종보스가 되었다 외전 1-10.txt")
        ["외전"]
        >>> extract_variant_flags("갓 오브 블랙필드 완결 합본.txt")
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
