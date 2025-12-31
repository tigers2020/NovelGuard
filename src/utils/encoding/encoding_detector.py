"""
인코딩 감지기 모듈

바이트 데이터에서 인코딩을 감지하는 기능을 제공합니다.
"""

import charset_normalizer

from utils.logger import get_logger
from utils.exceptions import FileEncodingError
from utils.constants import ENCODING_UNKNOWN, ENCODING_EMPTY
from utils.encoding.encoding_normalizer import EncodingNormalizer


class EncodingDetector:
    """인코딩 감지기 클래스.
    
    바이트 데이터에서 인코딩을 감지합니다.
    charset_normalizer를 사용합니다.
    """
    
    def __init__(self) -> None:
        """EncodingDetector 초기화."""
        self._logger = get_logger("EncodingDetector")
        self._normalizer = EncodingNormalizer()
    
    def detect(self, raw: bytes) -> str:
        """바이트 데이터에서 인코딩을 감지합니다.
        
        charset_normalizer를 사용하여 인코딩을 감지합니다.
        
        Args:
            raw: 원본 바이트 데이터
        
        Returns:
            감지된 인코딩 이름 (표준화됨). 감지 실패 시 DEFAULT_ENCODING 반환.
        
        Raises:
            FileEncodingError: 인코딩 감지 중 오류 발생 시
        
        Example:
            >>> detector = EncodingDetector()
            >>> data = "안녕하세요".encode("utf-8")
            >>> detector.detect(data)
            "utf-8"
        """
        if not raw:
            return ENCODING_EMPTY
        
        try:
            detected = charset_normalizer.detect(raw)
            if detected and detected.get("encoding"):
                encoding = detected["encoding"]
                return self._normalizer.normalize(encoding)
            return ENCODING_UNKNOWN
        except Exception as e:
            self._logger.warning(f"인코딩 감지 중 오류: {e}")
            raise FileEncodingError(f"인코딩 감지 실패: {str(e)}") from e

