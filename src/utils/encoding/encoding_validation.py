"""
인코딩 검증 유틸리티 모듈

해시 계산기에서 사용하는 인코딩 검증 로직을 공통화합니다.
"""

from pathlib import Path
from typing import Optional

from utils.exceptions import FileEncodingError
from utils.constants import (
    DEFAULT_ENCODING,
    ENCODING_UNKNOWN,
    ENCODING_EMPTY,
    ENCODING_NA,
    ENCODING_NOT_DETECTED,
)


def validate_confirmed_encoding(encoding: Optional[str], file_path: Path) -> str:
    """인코딩 값을 검증하고 정규화합니다.
    
    해시 계산기에서 사용하기 전에 인코딩 값을 검증하고 정규화합니다.
    - None 또는 ENCODING_NOT_DETECTED인 경우 ValueError 발생
    - ENCODING_UNKNOWN/EMPTY/NA는 DEFAULT_ENCODING으로 변환
    - 그 외는 그대로 반환
    
    Args:
        encoding: 검증할 인코딩 값 (FileRecord.encoding에서 전달받아야 함)
        file_path: 파일 경로 (에러 메시지용)
    
    Returns:
        검증 및 정규화된 인코딩 값
    
    Raises:
        ValueError: encoding이 None이거나 ENCODING_NOT_DETECTED인 경우
    
    Example:
        >>> validate_confirmed_encoding("utf-8", Path("test.txt"))
        "utf-8"
        >>> validate_confirmed_encoding("Unknown", Path("test.txt"))
        "utf-8"
        >>> validate_confirmed_encoding(None, Path("test.txt"))
        ValueError: encoding은 필수입니다...
    """
    # 인코딩이 None이거나 "-"인 경우 예외 발생
    if encoding is None or encoding == ENCODING_NOT_DETECTED:
        raise ValueError(
            f"encoding은 필수입니다 (None 또는 '-' 금지). "
            f"FileRecord.encoding에서 전달받아야 합니다: {file_path}"
        )
    
    # Unknown/Empty/N/A는 기본값으로 처리
    if encoding in (ENCODING_UNKNOWN, ENCODING_EMPTY, ENCODING_NA):
        return DEFAULT_ENCODING
    
    return encoding

