"""확장자 관련 유틸리티 함수."""
from typing import Final

# 빈 확장자 리스트는 모든 파일을 의미
EMPTY_EXTENSIONS: Final[list[str]] = []


def parse_extensions(extensions_str: str) -> list[str]:
    """확장자 문자열 파싱.
    
    Args:
        extensions_str: ".txt, .md, .log" 또는 "txt, md, log" 형식의 문자열.
                       빈 문자열이면 빈 리스트를 반환 (호출하는 쪽에서 기본값 처리).
    
    Returns:
        확장자 리스트 ['.txt', '.md', '.log'] (점 포함, 소문자).
        빈 문자열이면 빈 리스트 [].
    
    Examples:
        >>> parse_extensions(".txt, .md")
        ['.txt', '.md']
        >>> parse_extensions("txt, md, log")
        ['.txt', '.md', '.log']
        >>> parse_extensions("")
        []
        >>> parse_extensions("  ")
        []
    """
    if not extensions_str.strip():
        return []
    
    extensions = []
    for ext in extensions_str.split(','):
        ext = ext.strip()
        if ext:
            # 점이 없으면 추가
            if not ext.startswith('.'):
                ext = '.' + ext
            extensions.append(ext.lower())
    
    return extensions
