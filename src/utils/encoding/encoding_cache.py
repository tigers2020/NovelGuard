"""
인코딩 캐시 모듈

인코딩 감지 결과를 캐싱하는 기능을 제공합니다.
"""

import os
from pathlib import Path
from typing import Optional
from functools import lru_cache

from utils.logger import get_logger
from utils.constants import ENCODING_CACHE_SIZE, ENCODING_SAMPLE_SIZE, ENCODING_UNKNOWN
from utils.encoding.encoding_detector import EncodingDetector


class EncodingCache:
    """인코딩 캐시 클래스.
    
    인코딩 감지 결과를 LRU 캐시로 관리합니다.
    """
    
    def __init__(self, cache_size: int = ENCODING_CACHE_SIZE) -> None:
        """EncodingCache 초기화.
        
        Args:
            cache_size: 캐시 크기 (기본값: ENCODING_CACHE_SIZE)
        """
        self._logger = get_logger("EncodingCache")
        self._detector = EncodingDetector()
        self._cache_size = cache_size
        # LRU 캐시 함수 생성
        self._cached_detect = self._create_cached_function()
    
    def _create_cached_function(self):
        """캐시된 인코딩 감지 함수를 생성합니다."""
        @lru_cache(maxsize=self._cache_size)
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
                    return self._detector.detect(sample)
            except Exception as e:
                self._logger.warning(f"인코딩 감지 중 파일 읽기 오류: {path} - {e}")
                return ENCODING_UNKNOWN
        
        return _detect_encoding_cached
    
    def get_cache_key(self, path: Path) -> Optional[tuple[str, float, int]]:
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
    
    def get_cached(self, path: Path, sample_size: int = ENCODING_SAMPLE_SIZE) -> Optional[str]:
        """캐시에서 인코딩을 가져옵니다.
        
        Args:
            path: 파일 경로
            sample_size: 샘플 크기
        
        Returns:
            캐시된 인코딩 이름. 캐시에 없으면 None.
        """
        cache_key = self.get_cache_key(path)
        if cache_key:
            path_str, mtime, size = cache_key
            return self._cached_detect(path_str, mtime, size, sample_size)
        return None
    
    def clear(self) -> None:
        """인코딩 감지 캐시를 초기화합니다.
        
        테스트나 특수한 경우에 사용합니다.
        """
        self._cached_detect.cache_clear()

