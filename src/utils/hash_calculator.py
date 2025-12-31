"""
해시 계산 유틸리티

파일의 MD5 해시와 정규화 해시를 계산하는 기능을 제공합니다.
하위 호환성을 위해 함수 형태로 래핑된 API를 제공합니다.
"""

from pathlib import Path
from typing import Optional

from utils.hash_calculators.md5_hash_calculator import MD5HashCalculator
from utils.hash_calculators.normalized_hash_calculator import NormalizedHashCalculator
from utils.hash_calculators.anchor_hash_calculator import AnchorHashCalculator

# 전역 인스턴스 (성능 최적화)
_md5_calculator = MD5HashCalculator()
_normalized_calculator = NormalizedHashCalculator()
_anchor_calculator = AnchorHashCalculator()


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
    return _md5_calculator.calculate(file_path, encoding)


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
    return _normalized_calculator.calculate(file_path, encoding)


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
    return _anchor_calculator.calculate(file_path, encoding)
