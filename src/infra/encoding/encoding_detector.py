"""인코딩 감지기.

charset-normalizer 래핑.
"""

from pathlib import Path
from typing import Optional
from charset_normalizer import detect as detect_encoding
from common.errors import FileEncodingError
from common.logging import setup_logging

logger = setup_logging()


class EncodingDetector:
    """인코딩 감지기."""
    
    @staticmethod
    def detect(file_path: Path) -> tuple[Optional[str], float]:
        """파일 인코딩 감지.
        
        Args:
            file_path: 파일 경로
        
        Returns:
            (인코딩, 신뢰도)
        
        Raises:
            FileEncodingError: 감지 실패
        """
        try:
            result = detect_encoding(file_path.read_bytes())
            
            if result is None:
                return None, 0.0
            
            encoding = result.get('encoding')
            confidence = result.get('confidence', 0.0)
            
            return encoding, confidence
        except Exception as e:
            logger.error(f"인코딩 감지 실패: {file_path} - {e}")
            raise FileEncodingError(f"인코딩 감지 실패: {e}") from e
    
    @staticmethod
    def detect_from_bytes(data: bytes) -> tuple[Optional[str], float]:
        """바이트 데이터의 인코딩 감지.
        
        Args:
            data: 바이트 데이터
        
        Returns:
            (인코딩, 신뢰도)
        """
        try:
            result = detect_encoding(data)
            
            if result is None:
                return None, 0.0
            
            encoding = result.get('encoding')
            confidence = result.get('confidence', 0.0)
            
            return encoding, confidence
        except Exception as e:
            logger.error(f"인코딩 감지 실패: {e}")
            return None, 0.0
    
    @staticmethod
    def decode_text(file_path: Path, encoding: Optional[str] = None) -> str:
        """텍스트 파일 디코딩.
        
        Args:
            file_path: 파일 경로
            encoding: 인코딩 (None이면 자동 감지)
        
        Returns:
            디코딩된 텍스트
        
        Raises:
            FileEncodingError: 디코딩 실패
        """
        try:
            data = file_path.read_bytes()
            
            if encoding is None:
                encoding, _ = EncodingDetector.detect_from_bytes(data)
                if encoding is None:
                    encoding = 'utf-8'
            
            return data.decode(encoding, errors='replace')
        except Exception as e:
            logger.error(f"텍스트 디코딩 실패: {file_path} - {e}")
            raise FileEncodingError(f"텍스트 디코딩 실패: {e}") from e

