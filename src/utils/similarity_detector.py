"""
유사도 탐지 유틸리티 (v2)

datasketch 라이브러리를 사용하여 텍스트 파일의 유사도를 계산합니다.
MinHash, SimHash, LSH (Locality Sensitive Hashing) 기법을 활용합니다.
"""

from pathlib import Path
from typing import Optional

try:
    from datasketch import MinHash, MinHashLSH
    DATASKETCH_AVAILABLE = True
except ImportError:
    DATASKETCH_AVAILABLE = False

from utils.exceptions import FileEncodingError
from utils.constants import (
    DEFAULT_ENCODING,
    ENCODING_UNKNOWN,
    ENCODING_EMPTY,
    ENCODING_NA,
    ENCODING_NOT_DETECTED,
)


def compute_minhash(content: str, num_perm: int = 128) -> Optional[MinHash]:
    """텍스트 내용으로부터 MinHash를 계산합니다.
    
    MinHash는 텍스트의 유사도를 빠르게 계산하기 위한 locality-sensitive hashing 기법입니다.
    
    Args:
        content: 텍스트 내용
        num_perm: 순열 개수 (기본값: 128, 높을수록 정확하지만 느림)
    
    Returns:
        MinHash 객체. datasketch가 없으면 None.
    
    Example:
        >>> hash1 = compute_minhash("안녕하세요 반갑습니다")
        >>> hash2 = compute_minhash("안녕하세요 반가워요")
        >>> # hash1.jaccard(hash2)로 유사도 계산 가능
    """
    if not DATASKETCH_AVAILABLE:
        return None
    
    if not content:
        return MinHash(num_perm=num_perm)
    
    # 텍스트를 토큰으로 분리 (공백 기준)
    tokens = content.split()
    
    # MinHash 생성 및 업데이트
    m = MinHash(num_perm=num_perm)
    for token in tokens:
        m.update(token.encode('utf-8'))
    
    return m


def compute_simhash(content: str, num_perm: int = 128) -> Optional[MinHash]:
    """텍스트 내용으로부터 SimHash를 계산합니다.
    
    SimHash는 MinHash의 변형으로, 텍스트의 유사도를 계산합니다.
    현재는 MinHash를 사용하지만, 향후 SimHash 전용 구현으로 변경 가능.
    
    Args:
        content: 텍스트 내용
        num_perm: 순열 개수 (기본값: 128)
    
    Returns:
        MinHash 객체 (SimHash 대신). datasketch가 없으면 None.
    """
    return compute_minhash(content, num_perm=num_perm)


def calculate_file_similarity(
    file1_path: Path,
    file2_path: Path,
    encoding1: Optional[str] = None,
    encoding2: Optional[str] = None,
    num_perm: int = 128
) -> Optional[float]:
    """두 파일의 유사도를 계산합니다 (Jaccard similarity).
    
    Args:
        file1_path: 첫 번째 파일 경로
        file2_path: 두 번째 파일 경로
        encoding1: 첫 번째 파일 인코딩
        encoding2: 두 번째 파일 인코딩
        num_perm: MinHash 순열 개수
    
    Returns:
        유사도 (0.0 ~ 1.0). datasketch가 없거나 파일 읽기 실패 시 None.
    
    Raises:
        FileEncodingError: 파일 읽기 실패 시
    """
    if not DATASKETCH_AVAILABLE:
        return None
    
    # 인코딩 기본값 처리
    if encoding1 is None or encoding1 == ENCODING_NOT_DETECTED:
        encoding1 = DEFAULT_ENCODING
    if encoding2 is None or encoding2 == ENCODING_NOT_DETECTED:
        encoding2 = DEFAULT_ENCODING
    
    if encoding1 in (ENCODING_UNKNOWN, ENCODING_EMPTY, ENCODING_NA):
        encoding1 = DEFAULT_ENCODING
    if encoding2 in (ENCODING_UNKNOWN, ENCODING_EMPTY, ENCODING_NA):
        encoding2 = DEFAULT_ENCODING
    
    try:
        # 파일 읽기
        with open(file1_path, "r", encoding=encoding1, errors="replace") as f:
            content1 = f.read()
        
        with open(file2_path, "r", encoding=encoding2, errors="replace") as f:
            content2 = f.read()
        
        # MinHash 계산
        hash1 = compute_minhash(content1, num_perm=num_perm)
        hash2 = compute_minhash(content2, num_perm=num_perm)
        
        if hash1 is None or hash2 is None:
            return None
        
        # Jaccard similarity 계산
        similarity = hash1.jaccard(hash2)
        return similarity
        
    except UnicodeDecodeError as e:
        raise FileEncodingError(f"파일 인코딩 오류: {file1_path} 또는 {file2_path}") from e
    except (OSError, PermissionError) as e:
        raise FileEncodingError(f"파일 읽기 오류: {file1_path} 또는 {file2_path}") from e


def create_lsh_index(threshold: float = 0.5, num_perm: int = 128) -> Optional[MinHashLSH]:
    """LSH (Locality Sensitive Hashing) 인덱스를 생성합니다.
    
    대량의 파일에서 유사한 파일을 빠르게 찾기 위한 인덱스입니다.
    
    Args:
        threshold: 유사도 임계값 (0.0 ~ 1.0)
        num_perm: MinHash 순열 개수
    
    Returns:
        MinHashLSH 객체. datasketch가 없으면 None.
    
    Example:
        >>> lsh = create_lsh_index(threshold=0.8)
        >>> lsh.insert("file1", minhash1)
        >>> results = lsh.query(minhash2)  # 유사한 파일 찾기
    """
    if not DATASKETCH_AVAILABLE:
        return None
    
    return MinHashLSH(threshold=threshold, num_perm=num_perm)

