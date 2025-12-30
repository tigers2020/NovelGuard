"""
파일명 파싱 유틸리티

파일명에서 제목과 회차 범위를 추출하는 기능을 제공합니다.
"""

import re
from typing import Optional

from utils.text_normalizer import normalize_title


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
    
    # 회차 범위 패턴: "1-114", "1~158", "1-50화" 등
    # 숫자 패턴: "01권", "제1권", "Chapter 1" 등
    patterns = [
        r'\s+\d+[-~]\d+',  # "1-114", "1~158"
        r'\s+\d+[-~]\d+화',  # "1-50화"
        r'\s+\d+권',  # "01권", "1권"
        r'\s+제\d+권',  # "제1권"
        r'\s+Chapter\s+\d+',  # "Chapter 1"
        r'\s+Ch\.\s*\d+',  # "Ch. 1"
        r'\s+Ep\.\s*\d+',  # "Ep. 1"
        r'\s+\d+부',  # "1부"
    ]
    
    # 가장 먼저 매칭되는 패턴으로 제목 추출
    for pattern in patterns:
        match = re.search(pattern, name, re.IGNORECASE)
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
    
    # 회차 범위 패턴: "1-114", "1~158", "1-50화"
    patterns = [
        r'(\d+)[-~](\d+)화?',  # "1-114", "1~158", "1-50화"
    ]
    
    for pattern in patterns:
        match = re.search(pattern, name)
        if match:
            try:
                start = int(match.group(1))
                end = int(match.group(2))
                if start > 0 and end > 0 and start <= end:
                    return (start, end)
            except (ValueError, IndexError):
                continue
    
    # 패턴 매칭 실패
    return None

