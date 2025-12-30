"""
포맷터 유틸리티 모듈

데이터 포맷팅 관련 유틸리티 함수를 제공합니다.
"""

from .constants import BYTES_PER_KB


def format_file_size(size_bytes: int) -> str:
    """파일 크기를 읽기 쉬운 형식으로 변환합니다.
    
    바이트 단위의 파일 크기를 KB, MB, GB 등의 단위로 변환하여
    사용자 친화적인 문자열로 반환합니다.
    
    Args:
        size_bytes: 바이트 단위 파일 크기 (0 이상의 정수)
        
    Returns:
        포맷팅된 파일 크기 문자열 (예: "1.5 KB", "2.3 MB", "0 B")
        
    Examples:
        >>> format_file_size(0)
        '0 B'
        >>> format_file_size(1024)
        '1.00 KB'
        >>> format_file_size(1536)
        '1.50 KB'
        >>> format_file_size(1048576)
        '1.00 MB'
    """
    if size_bytes == 0:
        return "0 B"
    
    units = ["B", "KB", "MB", "GB"]
    unit_index = 0
    size = float(size_bytes)
    
    while size >= BYTES_PER_KB and unit_index < len(units) - 1:
        size /= BYTES_PER_KB
        unit_index += 1
    
    if unit_index == 0:
        return f"{int(size)} {units[unit_index]}"
    else:
        return f"{size:.2f} {units[unit_index]}"

