"""
정규화 해시 계산기 모듈

정규화된 텍스트의 해시를 계산하는 기능을 제공합니다.
"""

import hashlib
from pathlib import Path
from typing import Optional

from utils.exceptions import FileEncodingError
from utils.constants import (
    DEFAULT_ENCODING,
)
from utils.encoding.encoding_validation import validate_confirmed_encoding
from utils.text_normalizer import normalize_text_for_comparison


class NormalizedHashCalculator:
    """정규화 해시 계산기 클래스.
    
    정규화된 텍스트의 해시를 계산합니다.
    normalize_text_for_comparison()을 사용하여 정규화 후 해시 계산.
    
    Attributes:
        (없음)
    """
    
    def calculate(self, file_path: Path, encoding: Optional[str] = None) -> str:
        """정규화된 텍스트의 해시를 계산합니다.
        
        normalize_text_for_comparison()을 사용하여 정규화 후 해시 계산.
        정규화 규칙을 재사용합니다.
        
        Args:
            file_path: 해시를 계산할 파일 경로
            encoding: 파일 인코딩 (필수, FileRecord.encoding에서 전달받아야 함)
        
        Returns:
            정규화 해시값 (hex 문자열)
        
        Raises:
            ValueError: encoding이 None이거나 "-"인 경우
            FileEncodingError: 인코딩 오류 시
            OSError: 파일 읽기 실패 시
        """
        # 인코딩 검증 및 정규화
        encoding = validate_confirmed_encoding(encoding, file_path)
        
        try:
            # 파일 전체 읽기
            with open(file_path, "r", encoding=encoding, errors="replace") as f:
                content = f.read()
            
            # 정규화 후 해시 계산
            normalized = normalize_text_for_comparison(content)
            md5 = hashlib.md5()
            md5.update(normalized.encode(DEFAULT_ENCODING))
            
            return md5.hexdigest()
            
        except UnicodeDecodeError as e:
            raise FileEncodingError(f"파일 인코딩 오류: {file_path}") from e
        except (OSError, PermissionError) as e:
            raise FileEncodingError(f"파일 읽기 오류: {file_path}") from e

