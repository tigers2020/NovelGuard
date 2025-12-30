"""
해시 계산 유틸리티

파일의 MD5 해시와 정규화 해시를 계산하는 기능을 제공합니다.
"""

import hashlib
from pathlib import Path
from typing import Optional

import charset_normalizer

from utils.text_normalizer import normalize_text_for_comparison
from utils.exceptions import FileEncodingError


def calculate_md5_hash(file_path: Path, encoding: Optional[str] = None) -> str:
    """파일의 MD5 해시를 계산합니다.
    
    스트리밍 방식으로 메모리 효율적으로 처리합니다.
    
    Args:
        file_path: 해시를 계산할 파일 경로
        encoding: 파일 인코딩 (None이면 자동 감지)
    
    Returns:
        MD5 해시값 (hex 문자열)
    
    Raises:
        FileEncodingError: 인코딩 감지 실패 시
        OSError: 파일 읽기 실패 시
    
    Example:
        >>> hash_value = calculate_md5_hash(Path("test.txt"))
        >>> len(hash_value)
        32
    """
    md5 = hashlib.md5()
    chunk_size = 8192  # 8KB 청크
    
    try:
        # 인코딩 자동 감지
        if encoding is None:
            with open(file_path, "rb") as f:
                sample = f.read(32 * 1024)  # 32KB 샘플
                detected = charset_normalizer.detect(sample)
                encoding = detected.get("encoding") if detected else "utf-8"
                if not encoding:
                    encoding = "utf-8"
        
        # 텍스트 파일로 읽어서 해시 계산
        with open(file_path, "r", encoding=encoding, errors="replace") as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                # UTF-8 바이트로 변환하여 해시 계산
                md5.update(chunk.encode("utf-8"))
        
        return md5.hexdigest()
        
    except UnicodeDecodeError as e:
        raise FileEncodingError(f"파일 인코딩 오류: {file_path}") from e
    except (OSError, PermissionError) as e:
        raise FileEncodingError(f"파일 읽기 오류: {file_path}") from e


def calculate_normalized_hash(file_path: Path, encoding: Optional[str] = None) -> str:
    """정규화된 텍스트의 해시를 계산합니다 (v1.5용).
    
    normalize_text_for_comparison()을 사용하여 정규화 후 해시 계산.
    정규화 규칙을 재사용합니다.
    
    Args:
        file_path: 해시를 계산할 파일 경로
        encoding: 파일 인코딩 (None이면 자동 감지)
    
    Returns:
        정규화 해시값 (hex 문자열)
    
    Raises:
        FileEncodingError: 인코딩 감지 실패 시
        OSError: 파일 읽기 실패 시
    
    Example:
        >>> hash1 = calculate_normalized_hash(Path("file1.txt"))
        >>> hash2 = calculate_normalized_hash(Path("file2.txt"))
        >>> # 공백/줄바꿈 차이만 있으면 같은 해시
    """
    try:
        # 인코딩 자동 감지
        if encoding is None:
            with open(file_path, "rb") as f:
                sample = f.read(32 * 1024)  # 32KB 샘플
                detected = charset_normalizer.detect(sample)
                encoding = detected.get("encoding") if detected else "utf-8"
                if not encoding:
                    encoding = "utf-8"
        
        # 파일 전체 읽기
        with open(file_path, "r", encoding=encoding, errors="replace") as f:
            content = f.read()
        
        # 정규화 후 해시 계산
        normalized = normalize_text_for_comparison(content)
        md5 = hashlib.md5()
        md5.update(normalized.encode("utf-8"))
        
        return md5.hexdigest()
        
    except UnicodeDecodeError as e:
        raise FileEncodingError(f"파일 인코딩 오류: {file_path}") from e
    except (OSError, PermissionError) as e:
        raise FileEncodingError(f"파일 읽기 오류: {file_path}") from e

