"""
FileRecord 모델 테스트

FileRecord 모델의 검증 로직과 동작을 테스트합니다.
"""

import sys
import unittest
from pathlib import Path

from pydantic import ValidationError

# 프로젝트 루트를 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from models.file_record import FileRecord


class TestFileRecord(unittest.TestCase):
    """FileRecord 모델 테스트 클래스."""
    
    def test_create_valid_record(self) -> None:
        """유효한 FileRecord 생성 테스트."""
        record = FileRecord(
            path=Path("test.txt"),
            name="test.txt",
            size=1024,
            encoding="utf-8"
        )
        
        self.assertEqual(record.path, Path("test.txt"))
        self.assertEqual(record.name, "test.txt")
        self.assertEqual(record.size, 1024)
        self.assertEqual(record.encoding, "utf-8")
    
    def test_create_with_default_encoding(self) -> None:
        """기본 인코딩 값 테스트."""
        record = FileRecord(
            path=Path("test.txt"),
            name="test.txt",
            size=1024
        )
        
        self.assertEqual(record.encoding, "-")
    
    def test_name_validation_strips_whitespace(self) -> None:
        """파일명 공백 제거 검증 테스트."""
        record = FileRecord(
            path=Path("test.txt"),
            name="  test.txt  ",
            size=1024
        )
        
        self.assertEqual(record.name, "test.txt")
    
    def test_name_validation_rejects_empty(self) -> None:
        """빈 파일명 거부 테스트."""
        with self.assertRaises(ValidationError) as context:
            FileRecord(
                path=Path("test.txt"),
                name="",
                size=1024
            )
        
        errors = context.exception.errors()
        self.assertTrue(any("name" in str(error.get("loc", [])) for error in errors))
    
    def test_name_validation_rejects_whitespace_only(self) -> None:
        """공백만 있는 파일명 거부 테스트."""
        with self.assertRaises(ValidationError) as context:
            FileRecord(
                path=Path("test.txt"),
                name="   ",
                size=1024
            )
        
        errors = context.exception.errors()
        self.assertTrue(any("name" in str(error.get("loc", [])) for error in errors))
    
    def test_size_validation_rejects_negative(self) -> None:
        """음수 파일 크기 거부 테스트."""
        with self.assertRaises(ValidationError) as context:
            FileRecord(
                path=Path("test.txt"),
                name="test.txt",
                size=-1
            )
        
        errors = context.exception.errors()
        self.assertTrue(any("size" in str(error.get("loc", [])) for error in errors))
    
    def test_size_validation_accepts_zero(self) -> None:
        """0 바이트 파일 크기 허용 테스트."""
        record = FileRecord(
            path=Path("test.txt"),
            name="test.txt",
            size=0
        )
        
        self.assertEqual(record.size, 0)
    
    def test_path_validation_converts_string(self) -> None:
        """문자열 경로를 Path 객체로 변환 테스트."""
        record = FileRecord(
            path="test.txt",  # 문자열로 전달
            name="test.txt",
            size=1024
        )
        
        self.assertIsInstance(record.path, Path)
        self.assertEqual(record.path, Path("test.txt"))
    
    def test_path_validation_accepts_path_object(self) -> None:
        """Path 객체 경로 허용 테스트."""
        path_obj = Path("test.txt")
        record = FileRecord(
            path=path_obj,
            name="test.txt",
            size=1024
        )
        
        self.assertIsInstance(record.path, Path)
        self.assertEqual(record.path, path_obj)
    
    def test_record_equality(self) -> None:
        """FileRecord 동등성 테스트."""
        record1 = FileRecord(
            path=Path("test.txt"),
            name="test.txt",
            size=1024,
            encoding="utf-8"
        )
        
        record2 = FileRecord(
            path=Path("test.txt"),
            name="test.txt",
            size=1024,
            encoding="utf-8"
        )
        
        # Pydantic 모델은 값 기반 비교
        self.assertEqual(record1.path, record2.path)
        self.assertEqual(record1.name, record2.name)
        self.assertEqual(record1.size, record2.size)
        self.assertEqual(record1.encoding, record2.encoding)


if __name__ == "__main__":
    unittest.main()

