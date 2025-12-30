"""
인코딩 감지 유틸리티

파일 인코딩을 감지하는 기능을 통합 제공합니다.
중복 코드를 제거하고, LRU 캐시를 통해 성능을 최적화합니다.
"""

import os
from pathlib import Path
from typing import Optional
from functools import lru_cache
import charset_normalizer

from utils.logger import get_logger
from utils.exceptions import FileEncodingError
from utils.constants import (
    ENCODING_SAMPLE_SIZE,
    ENCODING_CACHE_SIZE,
    DEFAULT_ENCODING,
    ENCODING_UNKNOWN,
    ENCODING_EMPTY,
)


_logger = get_logger("EncodingDetector")


# 인코딩 이름 정규화 매핑
_ENCODING_NORMALIZATION = {
    "utf8": "utf-8",
    "utf-8": "utf-8",
    "euc-kr": "euc-kr",
    "cp949": "cp949",
    "latin1": "iso-8859-1",
    "iso-8859-1": "iso-8859-1",
}


def normalize_encoding_name(name: str) -> str:
    """인코딩 이름을 표준화합니다.
    
    utf8/utf-8 등 다양한 표기를 통일합니다.
    
    Args:
        name: 원본 인코딩 이름
        
    Returns:
        표준화된 인코딩 이름
        
    Example:
        >>> normalize_encoding_name("utf8")
        "utf-8"
        >>> normalize_encoding_name("UTF-8")
        "utf-8"
    """
    if not name:
        return DEFAULT_ENCODING
    
    name_lower = name.lower().strip()
    return _ENCODING_NORMALIZATION.get(name_lower, name_lower)


def detect_encoding_bytes(raw: bytes) -> str:
    """바이트 데이터에서 인코딩을 감지합니다.
    
    charset_normalizer를 사용하여 인코딩을 감지합니다.
    
    Args:
        raw: 원본 바이트 데이터
        
    Returns:
        감지된 인코딩 이름 (표준화됨). 감지 실패 시 DEFAULT_ENCODING 반환.
        
    Raises:
        FileEncodingError: 인코딩 감지 중 오류 발생 시
        
    Example:
        >>> data = "안녕하세요".encode("utf-8")
        >>> detect_encoding_bytes(data)
        "utf-8"
    """
    if not raw:
        return ENCODING_EMPTY
    
    try:
        detected = charset_normalizer.detect(raw)
        if detected and detected.get("encoding"):
            encoding = detected["encoding"]
            return normalize_encoding_name(encoding)
        return ENCODING_UNKNOWN
    except Exception as e:
        _logger.warning(f"인코딩 감지 중 오류: {e}")
        raise FileEncodingError(f"인코딩 감지 실패: {str(e)}") from e


def _get_cache_key(path: Path) -> Optional[tuple[str, float, int]]:
    """캐시 키를 생성합니다.
    
    Args:
        path: 파일 경로
        
    Returns:
        (path_str, mtime, size) 튜플. 파일이 없으면 None.
    """
    try:
        stat = path.stat()
        return (str(path), stat.st_mtime, stat.st_size)
    except (OSError, FileNotFoundError):
        return None


@lru_cache(maxsize=ENCODING_CACHE_SIZE)
def _detect_encoding_cached(path_str: str, mtime: float, size: int, sample_size: int) -> str:
    """캐시된 인코딩 감지 함수.
    
    내부 함수로, lru_cache 데코레이터를 사용합니다.
    실제 파일 읽기는 이 함수 내부에서 수행됩니다.
    
    Args:
        path_str: 파일 경로 문자열
        mtime: 파일 수정 시간
        size: 파일 크기
        sample_size: 샘플 크기
        
    Returns:
        감지된 인코딩 이름
    """
    path = Path(path_str)
    try:
        with open(path, "rb") as f:
            sample = f.read(sample_size)
            return detect_encoding_bytes(sample)
    except Exception as e:
        _logger.warning(f"인코딩 감지 중 파일 읽기 오류: {path} - {e}")
        return ENCODING_UNKNOWN


def detect_encoding_path(path: Path, sample_size: int = ENCODING_SAMPLE_SIZE, use_cache: bool = True) -> str:
    """파일 경로에서 인코딩을 감지합니다.
    
    파일의 샘플만 읽어서 인코딩을 감지합니다.
    LRU 캐시를 사용하여 같은 파일의 재감지를 방지합니다.
    
    Args:
        path: 파일 경로
        sample_size: 샘플 크기 (바이트, 기본값: ENCODING_SAMPLE_SIZE)
        use_cache: 캐시 사용 여부 (기본값: True)
        
    Returns:
        감지된 인코딩 이름 (표준화됨). 감지 실패 시 DEFAULT_ENCODING 반환.
        
    Raises:
        FileEncodingError: 인코딩 감지 중 오류 발생 시
        
    Example:
        >>> path = Path("test.txt")
        >>> detect_encoding_path(path)
        "utf-8"
    """
    if not path.exists():
        raise FileEncodingError(f"파일이 존재하지 않습니다: {path}")
    
    if path.stat().st_size == 0:
        return ENCODING_EMPTY
    
    try:
        if use_cache:
            cache_key = _get_cache_key(path)
            if cache_key:
                path_str, mtime, size = cache_key
                return _detect_encoding_cached(path_str, mtime, size, sample_size)
        
        # 캐시 미사용 또는 캐시 키 생성 실패 시 직접 감지
        with open(path, "rb") as f:
            sample = f.read(sample_size)
            return detect_encoding_bytes(sample)
            
    except (OSError, PermissionError) as e:
        _logger.warning(f"인코딩 감지 중 파일 접근 오류: {path} - {e}")
        raise FileEncodingError(f"파일 접근 오류: {path}") from e
    except Exception as e:
        _logger.error(f"인코딩 감지 중 예상치 못한 오류: {path} - {e}", exc_info=True)
        raise FileEncodingError(f"인코딩 감지 실패: {path}") from e


def clear_encoding_cache() -> None:
    """인코딩 감지 캐시를 초기화합니다.
    
    테스트나 특수한 경우에 사용합니다.
    """
    _detect_encoding_cached.cache_clear()

