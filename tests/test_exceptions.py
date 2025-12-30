"""
예외 클래스 테스트

커스텀 예외 클래스의 동작을 테스트합니다.
"""

import sys
import unittest
from pathlib import Path

# 프로젝트 루트를 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from utils.exceptions import (
    NovelGuardError,
    FileScanError,
    FileEncodingError,
)


class TestExceptions(unittest.TestCase):
    """예외 클래스 테스트 클래스."""
    
    def test_novel_guard_error_is_exception(self) -> None:
        """NovelGuardError가 Exception을 상속하는지 테스트."""
        self.assertTrue(issubclass(NovelGuardError, Exception))
    
    def test_file_scan_error_is_novel_guard_error(self) -> None:
        """FileScanError가 NovelGuardError를 상속하는지 테스트."""
        self.assertTrue(issubclass(FileScanError, NovelGuardError))
        self.assertTrue(issubclass(FileScanError, Exception))
    
    def test_file_encoding_error_is_novel_guard_error(self) -> None:
        """FileEncodingError가 NovelGuardError를 상속하는지 테스트."""
        self.assertTrue(issubclass(FileEncodingError, NovelGuardError))
        self.assertTrue(issubclass(FileEncodingError, Exception))
    
    def test_raise_novel_guard_error(self) -> None:
        """NovelGuardError 발생 테스트."""
        with self.assertRaises(NovelGuardError):
            raise NovelGuardError("테스트 오류")
    
    def test_raise_file_scan_error(self) -> None:
        """FileScanError 발생 테스트."""
        with self.assertRaises(FileScanError):
            raise FileScanError("파일 스캔 오류")
        
        # NovelGuardError로도 캐치 가능한지 확인
        with self.assertRaises(NovelGuardError):
            raise FileScanError("파일 스캔 오류")
    
    def test_raise_file_encoding_error(self) -> None:
        """FileEncodingError 발생 테스트."""
        with self.assertRaises(FileEncodingError):
            raise FileEncodingError("인코딩 오류")
        
        # NovelGuardError로도 캐치 가능한지 확인
        with self.assertRaises(NovelGuardError):
            raise FileEncodingError("인코딩 오류")
    
    def test_exception_message(self) -> None:
        """예외 메시지 전달 테스트."""
        message = "테스트 오류 메시지"
        error = NovelGuardError(message)
        self.assertEqual(str(error), message)
    
    def test_exception_inheritance_chain(self) -> None:
        """예외 상속 체인 테스트."""
        # FileScanError는 NovelGuardError와 Exception 모두의 인스턴스
        error = FileScanError("테스트")
        self.assertIsInstance(error, FileScanError)
        self.assertIsInstance(error, NovelGuardError)
        self.assertIsInstance(error, Exception)


if __name__ == "__main__":
    unittest.main()

