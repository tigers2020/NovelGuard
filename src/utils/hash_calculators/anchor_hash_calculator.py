"""
앵커 해시 계산기 모듈

파일의 앵커 해시(부분 해싱)를 계산하는 기능을 제공합니다.
"""

import hashlib
from pathlib import Path
from typing import Optional

try:
    import xxhash
    XXHASH_AVAILABLE = True
except ImportError:
    XXHASH_AVAILABLE = False

from utils.exceptions import FileEncodingError
from utils.constants import (
    ANCHOR_SIZE,
    DEFAULT_ENCODING,
)
from utils.encoding.encoding_validation import validate_confirmed_encoding
from utils.text_normalizer import normalize_text_for_comparison


class AnchorHashCalculator:
    """앵커 해시 계산기 클래스.
    
    파일의 앵커 해시를 계산합니다.
    앞부분, 중간 부분, 뒷부분의 해시를 계산하여 후보 생성에 사용합니다.
    전체 파일을 읽지 않고 부분만 읽어서 효율적으로 처리합니다.
    
    Attributes:
        _anchor_size: 앵커 크기 (기본값: ANCHOR_SIZE)
    """
    
    def __init__(self, anchor_size: int = ANCHOR_SIZE) -> None:
        """AnchorHashCalculator 초기화.
        
        Args:
            anchor_size: 앵커 크기 (기본값: ANCHOR_SIZE)
        """
        self._anchor_size = anchor_size
    
    def calculate(self, file_path: Path, encoding: Optional[str] = None) -> dict[str, str]:
        """파일의 앵커 해시를 계산합니다.
        
        앞부분, 중간 부분, 뒷부분의 해시를 계산하여 후보 생성에 사용합니다.
        전체 파일을 읽지 않고 부분만 읽어서 효율적으로 처리합니다.
        파일을 한 번만 열어서 3개 청크를 모두 읽어 I/O 오버헤드를 최소화합니다.
        
        Args:
            file_path: 해시를 계산할 파일 경로
            encoding: 파일 인코딩 (필수, FileRecord.encoding에서 전달받아야 함)
        
        Returns:
            {"head": "...", "mid": "...", "tail": "..."} 형태의 딕셔너리
        
        Raises:
            ValueError: encoding이 None이거나 "-"인 경우
            FileEncodingError: 인코딩 오류 시
            OSError: 파일 읽기 실패 시
        """
        # 인코딩 검증 및 정규화
        encoding = validate_confirmed_encoding(encoding, file_path)
        
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
                head_bytes = f.read(self._anchor_size)
                head_hash = _hash_chunk(head_bytes)
                
                # mid: offset=max(0, size//2 - anchor_size//2)
                mid_offset = max(0, file_size // 2 - self._anchor_size // 2)
                f.seek(mid_offset)
                mid_bytes = f.read(self._anchor_size)
                mid_hash = _hash_chunk(mid_bytes)
                
                # tail: offset=max(0, size - anchor_size)
                tail_offset = max(0, file_size - self._anchor_size)
                f.seek(tail_offset)
                tail_bytes = f.read(self._anchor_size)
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

