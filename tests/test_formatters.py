"""
포맷터 유틸리티 테스트

format_file_size 함수의 동작을 테스트합니다.
"""

import sys
import unittest
from pathlib import Path

# 프로젝트 루트를 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from utils.formatters import format_file_size


class TestFormatFileSize(unittest.TestCase):
    """format_file_size 함수 테스트 클래스."""
    
    def test_zero_bytes(self) -> None:
        """0 바이트 테스트."""
        result = format_file_size(0)
        self.assertEqual(result, "0 B")
    
    def test_bytes_less_than_kb(self) -> None:
        """1KB 미만 바이트 테스트."""
        result = format_file_size(512)
        self.assertEqual(result, "512 B")
    
    def test_exactly_one_kb(self) -> None:
        """정확히 1KB 테스트."""
        result = format_file_size(1024)
        self.assertEqual(result, "1.00 KB")
    
    def test_kb_with_decimal(self) -> None:
        """소수점이 있는 KB 테스트."""
        result = format_file_size(1536)  # 1.5 KB
        self.assertEqual(result, "1.50 KB")
    
    def test_exactly_one_mb(self) -> None:
        """정확히 1MB 테스트."""
        result = format_file_size(1048576)  # 1024 * 1024
        self.assertEqual(result, "1.00 MB")
    
    def test_mb_with_decimal(self) -> None:
        """소수점이 있는 MB 테스트."""
        result = format_file_size(1572864)  # 1.5 MB
        self.assertEqual(result, "1.50 MB")
    
    def test_exactly_one_gb(self) -> None:
        """정확히 1GB 테스트."""
        result = format_file_size(1073741824)  # 1024 * 1024 * 1024
        self.assertEqual(result, "1.00 GB")
    
    def test_gb_with_decimal(self) -> None:
        """소수점이 있는 GB 테스트."""
        result = format_file_size(1610612736)  # 1.5 GB
        self.assertEqual(result, "1.50 GB")
    
    def test_large_size(self) -> None:
        """큰 파일 크기 테스트."""
        # 2.5 GB
        result = format_file_size(2684354560)
        self.assertEqual(result, "2.50 GB")
    
    def test_very_small_size(self) -> None:
        """매우 작은 파일 크기 테스트."""
        result = format_file_size(1)
        self.assertEqual(result, "1 B")
    
    def test_kb_boundary(self) -> None:
        """KB 경계값 테스트."""
        # 1023 바이트 (KB 미만)
        result = format_file_size(1023)
        self.assertEqual(result, "1023 B")
        
        # 1024 바이트 (정확히 1KB)
        result = format_file_size(1024)
        self.assertEqual(result, "1.00 KB")
        
        # 1025 바이트 (1KB 초과)
        result = format_file_size(1025)
        self.assertEqual(result, "1.00 KB")
    
    def test_mb_boundary(self) -> None:
        """MB 경계값 테스트."""
        # 1048575 바이트 (MB 미만, 약 1024KB)
        result = format_file_size(1048575)
        # 1048575 / 1024 = 1023.999... KB, 반올림하면 1024.00 KB
        self.assertEqual(result, "1024.00 KB")
        
        # 1048576 바이트 (정확히 1MB)
        result = format_file_size(1048576)
        self.assertEqual(result, "1.00 MB")


if __name__ == "__main__":
    unittest.main()

