"""
MD5 해시 계산기 모듈

파일의 MD5 해시를 계산하는 기능을 제공합니다.
"""

import hashlib
from pathlib import Path
from typing import Optional

from utils.exceptions import FileEncodingError
from utils.constants import (
    CHUNK_SIZE,
    DEFAULT_ENCODING,
)
from utils.encoding.encoding_validation import validate_confirmed_encoding


class MD5HashCalculator:
    """MD5 해시 계산기 클래스.
    
    파일의 MD5 해시를 계산합니다.
    스트리밍 방식으로 메모리 효율적으로 처리합니다.
    
    Attributes:
        _chunk_size: 청크 크기 (기본값: CHUNK_SIZE)
    """
    
    def __init__(self, chunk_size: int = CHUNK_SIZE) -> None:
        """MD5HashCalculator 초기화.
        
        Args:
            chunk_size: 청크 크기 (기본값: CHUNK_SIZE)
        """
        self._chunk_size = chunk_size
    
    def calculate(self, file_path: Path, encoding: Optional[str] = None) -> str:
        """파일의 MD5 해시를 계산합니다.
        
        스트리밍 방식으로 메모리 효율적으로 처리합니다.
        
        Args:
            file_path: 해시를 계산할 파일 경로
            encoding: 파일 인코딩 (필수, FileRecord.encoding에서 전달받아야 함)
        
        Returns:
            MD5 해시값 (hex 문자열)
        
        Raises:
            ValueError: encoding이 None이거나 "-"인 경우
            FileEncodingError: 인코딩 오류 시
            OSError: 파일 읽기 실패 시
        """
        # 인코딩 검증 및 정규화
        encoding = validate_confirmed_encoding(encoding, file_path)
        
        try:
            md5 = hashlib.md5()
            
            # 텍스트 파일로 읽어서 해시 계산
            with open(file_path, "r", encoding=encoding, errors="replace") as f:
                while True:
                    chunk = f.read(self._chunk_size)
                    if not chunk:
                        break
                    # UTF-8 바이트로 변환하여 해시 계산
                    md5.update(chunk.encode(DEFAULT_ENCODING))
            
            return md5.hexdigest()
            
        except UnicodeDecodeError as e:
            raise FileEncodingError(f"파일 인코딩 오류: {file_path}") from e
        except (OSError, PermissionError) as e:
            raise FileEncodingError(f"파일 읽기 오류: {file_path}") from e

