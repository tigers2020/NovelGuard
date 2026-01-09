"""지문 생성기.

빠른 지문 및 SimHash 생성.
"""

import hashlib
import xxhash
from pathlib import Path
from typing import Optional
from common.errors import NovelGuardError
from common.logging import setup_logging

logger = setup_logging()


class FingerprintGenerator:
    """지문 생성기."""
    
    @staticmethod
    def generate_fast_fingerprint(
        file_path: Path,
        head_size: int = 1024,
        mid_offset: Optional[int] = None,
        mid_size: int = 1024,
        tail_size: int = 1024
    ) -> str:
        """빠른 지문 생성 (head/mid/tail 해시).
        
        Args:
            file_path: 파일 경로
            head_size: 헤드 크기 (bytes)
            mid_offset: 중간 오프셋 (None이면 파일 크기의 절반)
            mid_size: 중간 크기 (bytes)
            tail_size: 테일 크기 (bytes)
        
        Returns:
            지문 (hex)
        """
        try:
            file_size = file_path.stat().st_size
            
            with open(file_path, "rb") as f:
                # Head
                head_data = f.read(head_size)
                
                # Mid
                if mid_offset is None:
                    mid_offset = file_size // 2
                f.seek(max(0, mid_offset - mid_size // 2))
                mid_data = f.read(mid_size)
                
                # Tail
                if file_size > tail_size:
                    f.seek(file_size - tail_size)
                else:
                    f.seek(0)
                tail_data = f.read(tail_size)
            
            # xxhash로 빠른 해시 계산
            hasher = xxhash.xxh64()
            hasher.update(head_data)
            hasher.update(mid_data)
            hasher.update(tail_data)
            
            return hasher.hexdigest()
        except Exception as e:
            logger.error(f"빠른 지문 생성 실패: {file_path} - {e}")
            raise NovelGuardError(f"빠른 지문 생성 실패: {e}") from e
    
    @staticmethod
    def generate_simhash(data: bytes, hash_bits: int = 64) -> int:
        """SimHash 생성.
        
        Args:
            data: 바이트 데이터
            hash_bits: 해시 비트 수 (32 또는 64)
        
        Returns:
            SimHash 값 (정수)
        """
        if hash_bits == 64:
            return xxhash.xxh64(data).intdigest()
        elif hash_bits == 32:
            return xxhash.xxh32(data).intdigest()
        else:
            raise ValueError(f"지원하지 않는 해시 비트 수: {hash_bits}")
    
    @staticmethod
    def generate_text_fingerprint(text: str) -> str:
        """텍스트 지문 생성 (정규화 후 해시).
        
        Args:
            text: 텍스트
        
        Returns:
            지문 (hex)
        """
        # 간단한 정규화 (실제로는 더 복잡한 정규화 필요)
        normalized = text.strip().lower()
        
        # SHA256 해시
        return hashlib.sha256(normalized.encode('utf-8')).hexdigest()

