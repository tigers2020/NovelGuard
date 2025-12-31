"""
인코딩 감지 유틸리티

파일 인코딩을 감지하는 기능을 통합 제공합니다.
하위 호환성을 위해 함수 형태로 래핑된 API를 제공합니다.
"""

from pathlib import Path
from typing import Optional

from utils.logger import get_logger
from utils.exceptions import FileEncodingError
from utils.constants import (
    ENCODING_SAMPLE_SIZE,
    ENCODING_EMPTY,
)
from utils.encoding.encoding_detector import EncodingDetector
from utils.encoding.encoding_cache import EncodingCache
from utils.encoding.encoding_normalizer import EncodingNormalizer

_logger = get_logger("EncodingDetector")

# 전역 인스턴스 (성능 최적화)
_encoding_detector = EncodingDetector()
_encoding_cache = EncodingCache()
_encoding_normalizer = EncodingNormalizer()


def normalize_encoding_name(name: str) -> str:
    """인코딩 이름을 표준화합니다.
    
    하위 호환성을 위한 함수 래퍼입니다.
    실제 구현은 EncodingNormalizer.normalize()에 있습니다.
    
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
    
    Note:
        이 함수는 하위 호환성을 위한 래퍼입니다.
        새로운 코드에서는 EncodingNormalizer를 직접 사용하는 것을 권장합니다.
    """
    return _encoding_normalizer.normalize(name)


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
    return _encoding_detector.detect(raw)


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
            cached_result = _encoding_cache.get_cached(path, sample_size)
            if cached_result is not None:
                return cached_result
        
        # 캐시 미사용 또는 캐시에 없을 시 직접 감지
        with open(path, "rb") as f:
            sample = f.read(sample_size)
            return _encoding_detector.detect(sample)
            
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
    _encoding_cache.clear()

