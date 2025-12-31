"""
텍스트 정규화 유틸리티

파일명과 본문 텍스트를 정규화하는 기능을 제공합니다.
하위 호환성을 위해 함수 형태로 래핑된 API를 제공합니다.
"""

from typing import Set

from utils.normalizers.title_normalizer import TitleNormalizer
from utils.normalizers.text_normalizer import TextNormalizer

# 전역 인스턴스 (성능 최적화)
_title_normalizer = TitleNormalizer()
_text_normalizer = TextNormalizer()

# 꼬리표 제거용 키워드 집합 (하위 호환성)
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
    return _title_normalizer.normalize(title)


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
    return _text_normalizer.normalize(content)

