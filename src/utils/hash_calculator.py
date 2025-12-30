"""
해시 계산 유틸리티

파일의 MD5 해시와 정규화 해시를 계산하는 기능을 제공합니다.
"""

import hashlib
from pathlib import Path
from typing import Optional

try:
    import xxhash
    XXHASH_AVAILABLE = True
except ImportError:
    XXHASH_AVAILABLE = False

from utils.text_normalizer import normalize_text_for_comparison
from utils.exceptions import FileEncodingError
from utils.constants import (
    CHUNK_SIZE,
    ANCHOR_SIZE,
    DEFAULT_ENCODING,
    ENCODING_UNKNOWN,
    ENCODING_EMPTY,
    ENCODING_NA,
    ENCODING_NOT_DETECTED,
)


def calculate_md5_hash(file_path: Path, encoding: Optional[str] = None) -> str:
    """파일의 MD5 해시를 계산합니다.
    
    스트리밍 방식으로 메모리 효율적으로 처리합니다.
    
    Args:
        file_path: 해시를 계산할 파일 경로
        encoding: 파일 인코딩 (필수, FileRecord.encoding에서 전달받아야 함)
    
    Returns:
        MD5 해시값 (hex 문자열)
    
    Raises:
        ValueError: encoding이 None이거나 "-"인 경우 (스캔 단계에서 이미 확정되어야 함)
        FileEncodingError: 인코딩 오류 시
        OSError: 파일 읽기 실패 시
    
    Example:
        >>> hash_value = calculate_md5_hash(Path("test.txt"), encoding="utf-8")
        >>> len(hash_value)
        32
    """
    # 인코딩이 None이거나 "-"인 경우 예외 발생 (스캔 단계에서 이미 확정되어야 함)
    if encoding is None or encoding == ENCODING_NOT_DETECTED:
        raise ValueError(
            f"encoding은 필수입니다 (None 또는 '-' 금지). "
            f"FileRecord.encoding에서 전달받아야 합니다: {file_path}"
        )
    
    # Unknown/Empty/N/A는 기본값으로 처리
    if encoding in (ENCODING_UNKNOWN, ENCODING_EMPTY, ENCODING_NA):
        encoding = DEFAULT_ENCODING
    
    try:
        md5 = hashlib.md5()
        
        # 텍스트 파일로 읽어서 해시 계산
        with open(file_path, "r", encoding=encoding, errors="replace") as f:
            while True:
                chunk = f.read(CHUNK_SIZE)
                if not chunk:
                    break
                # UTF-8 바이트로 변환하여 해시 계산
                md5.update(chunk.encode(DEFAULT_ENCODING))
        
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
        encoding: 파일 인코딩 (필수, FileRecord.encoding에서 전달받아야 함)
    
    Returns:
        정규화 해시값 (hex 문자열)
    
    Raises:
        ValueError: encoding이 None이거나 "-"인 경우 (스캔 단계에서 이미 확정되어야 함)
        FileEncodingError: 인코딩 오류 시
        OSError: 파일 읽기 실패 시
    
    Example:
        >>> hash1 = calculate_normalized_hash(Path("file1.txt"), encoding="utf-8")
        >>> hash2 = calculate_normalized_hash(Path("file2.txt"), encoding="utf-8")
        >>> # 공백/줄바꿈 차이만 있으면 같은 해시
    """
    # 인코딩이 None이거나 "-"인 경우 예외 발생 (스캔 단계에서 이미 확정되어야 함)
    if encoding is None or encoding == ENCODING_NOT_DETECTED:
        raise ValueError(
            f"encoding은 필수입니다 (None 또는 '-' 금지). "
            f"FileRecord.encoding에서 전달받아야 합니다: {file_path}"
        )
    
    # Unknown/Empty/N/A는 기본값으로 처리
    if encoding in (ENCODING_UNKNOWN, ENCODING_EMPTY, ENCODING_NA):
        encoding = DEFAULT_ENCODING
    
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


def compute_anchor_hashes(file_path: Path, encoding: Optional[str] = None) -> dict[str, str]:
    """파일의 앵커 해시를 계산합니다 (부분 해싱).
    
    앞부분, 중간 부분, 뒷부분의 해시를 계산하여 후보 생성에 사용합니다.
    전체 파일을 읽지 않고 부분만 읽어서 효율적으로 처리합니다.
    파일을 한 번만 열어서 3개 청크를 모두 읽어 I/O 오버헤드를 최소화합니다.
    
    Args:
        file_path: 해시를 계산할 파일 경로
        encoding: 파일 인코딩 (필수, FileRecord.encoding에서 전달받아야 함)
    
    Returns:
        {"head": "...", "mid": "...", "tail": "..."} 형태의 딕셔너리
    
    Raises:
        ValueError: encoding이 None이거나 "-"인 경우 (스캔 단계에서 이미 확정되어야 함)
        FileEncodingError: 인코딩 오류 시
        OSError: 파일 읽기 실패 시
    
    Example:
        >>> hashes = compute_anchor_hashes(Path("test.txt"), encoding="utf-8")
        >>> "head" in hashes
        True
        >>> "mid" in hashes
        True
        >>> "tail" in hashes
        True
    """
    # 인코딩이 None이거나 "-"인 경우 예외 발생 (스캔 단계에서 이미 확정되어야 함)
    if encoding is None or encoding == ENCODING_NOT_DETECTED:
        raise ValueError(
            f"encoding은 필수입니다 (None 또는 '-' 금지). "
            f"FileRecord.encoding에서 전달받아야 합니다: {file_path}"
        )
    
    # Unknown/Empty/N/A는 기본값으로 처리
    if encoding in (ENCODING_UNKNOWN, ENCODING_EMPTY, ENCODING_NA):
        encoding = DEFAULT_ENCODING
    
    try:
        # 파일 크기 확인
        file_size = file_path.stat().st_size
        
        if file_size == 0:
            # 빈 파일은 모두 같은 해시 반환
            if XXHASH_AVAILABLE:
                empty_hash = xxhash.xxh64().hexdigest()
            else:
                empty_hash = hashlib.md5().hexdigest()
            return {"head": empty_hash, "mid": empty_hash, "tail": empty_hash}
        
        # 파일을 한 번만 열고 3개 청크를 모두 읽기 (I/O 최적화)
        def _hash_chunk(chunk_bytes: bytes) -> str:
            """바이트 청크를 정규화 후 해시 계산.
            
            xxhash를 사용하여 빠른 해시 계산 (MD5 대비 10-20배 빠름).
            xxhash가 없으면 MD5로 폴백.
            """
            if not chunk_bytes:
                if XXHASH_AVAILABLE:
                    return xxhash.xxh64().hexdigest()
                return hashlib.md5().hexdigest()
            
            # 인코딩으로 디코딩
            try:
                chunk_text = chunk_bytes.decode(encoding, errors="replace")
            except Exception:
                # 디코딩 실패 시 UTF-8로 재시도
                chunk_text = chunk_bytes.decode(DEFAULT_ENCODING, errors="replace")
            
            # 정규화
            normalized = normalize_text_for_comparison(chunk_text)
            normalized_bytes = normalized.encode(DEFAULT_ENCODING)
            
            # 해시 계산 (xxhash 우선, 없으면 MD5)
            if XXHASH_AVAILABLE:
                return xxhash.xxh64(normalized_bytes).hexdigest()
            else:
                md5_hash = hashlib.md5()
                md5_hash.update(normalized_bytes)
                return md5_hash.hexdigest()
        
        # 파일을 한 번만 열고 필요한 모든 청크 읽기
        with open(file_path, "rb") as f:
            # head: offset=0
            f.seek(0)
            head_bytes = f.read(ANCHOR_SIZE)
            head_hash = _hash_chunk(head_bytes)
            
            # mid: offset=max(0, size//2 - anchor_size//2)
            mid_offset = max(0, file_size // 2 - ANCHOR_SIZE // 2)
            f.seek(mid_offset)
            mid_bytes = f.read(ANCHOR_SIZE)
            mid_hash = _hash_chunk(mid_bytes)
            
            # tail: offset=max(0, size - anchor_size)
            tail_offset = max(0, file_size - ANCHOR_SIZE)
            f.seek(tail_offset)
            tail_bytes = f.read(ANCHOR_SIZE)
            tail_hash = _hash_chunk(tail_bytes)
        
        return {
            "head": head_hash,
            "mid": mid_hash,
            "tail": tail_hash
        }
        
    except UnicodeDecodeError as e:
        raise FileEncodingError(f"파일 인코딩 오류: {file_path}") from e
    except (OSError, PermissionError) as e:
        raise FileEncodingError(f"파일 읽기 오류: {file_path}") from e
