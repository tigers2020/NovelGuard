"""
파일명 파싱 유틸리티

파일명에서 제목과 회차 범위를 추출하는 기능을 제공합니다.
하위 호환성을 위해 함수 형태로 래핑된 API를 제공합니다.
"""

from typing import Optional

from utils.parsers.title_extractor import TitleExtractor
from utils.parsers.episode_extractor import EpisodeExtractor
from utils.parsers.variant_flag_extractor import VariantFlagExtractor

# 전역 인스턴스 (성능 최적화)
_title_extractor = TitleExtractor()
_episode_extractor = EpisodeExtractor()
_variant_flag_extractor = VariantFlagExtractor()


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
    return _title_extractor.extract(filename)


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
    return _title_extractor.extract_normalized(filename)


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
    return _episode_extractor.extract_range(filename)


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
    return _episode_extractor.extract_base_title(filename)


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
    return _episode_extractor.extract_end(filename)


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
    return _variant_flag_extractor.extract(filename)
