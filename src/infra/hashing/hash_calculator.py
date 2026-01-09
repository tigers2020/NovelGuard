"""해시 계산기.

MD5, SHA256 계산.
"""

import hashlib
from pathlib import Path
from typing import Optional
from common.errors import NovelGuardError
from common.logging import setup_logging

logger = setup_logging()


class HashCalculator:
    """해시 계산기."""
    
    @staticmethod
    def calculate_md5(file_path: Path) -> str:
        """MD5 해시 계산.
        
        Args:
            file_path: 파일 경로
        
        Returns:
            MD5 해시 (hex)
        
        Raises:
            NovelGuardError: 파일 읽기 실패
        """
        try:
            hash_md5 = hashlib.md5()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception as e:
            logger.error(f"MD5 계산 실패: {file_path} - {e}")
            raise NovelGuardError(f"MD5 계산 실패: {e}") from e
    
    @staticmethod
    def calculate_sha256(file_path: Path) -> str:
        """SHA256 해시 계산.
        
        Args:
            file_path: 파일 경로
        
        Returns:
            SHA256 해시 (hex)
        
        Raises:
            NovelGuardError: 파일 읽기 실패
        """
        try:
            hash_sha256 = hashlib.sha256()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except Exception as e:
            logger.error(f"SHA256 계산 실패: {file_path} - {e}")
            raise NovelGuardError(f"SHA256 계산 실패: {e}") from e
    
    @staticmethod
    def calculate_hash(data: bytes, algorithm: str = "sha256") -> str:
        """바이트 데이터의 해시 계산.
        
        Args:
            data: 바이트 데이터
            algorithm: 해시 알고리즘 ("md5" | "sha256")
        
        Returns:
            해시 (hex)
        """
        if algorithm == "md5":
            return hashlib.md5(data).hexdigest()
        elif algorithm == "sha256":
            return hashlib.sha256(data).hexdigest()
        else:
            raise ValueError(f"지원하지 않는 알고리즘: {algorithm}")

