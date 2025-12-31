"""
무결성 검사기 테스트

IntegrityChecker의 동작을 테스트합니다.
"""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

# 프로젝트 루트를 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from models.file_record import FileRecord
from checkers.integrity_checker import IntegrityChecker, IntegrityIssue
from utils.constants import (
    INTEGRITY_ISSUE_CODE_EMPTY_FILE,
    INTEGRITY_ISSUE_CODE_READ_ERROR,
    INTEGRITY_ISSUE_CODE_DECODE_ERROR,
)


class TestIntegrityChecker(unittest.TestCase):
    """IntegrityChecker 테스트 클래스."""
    
    def setUp(self) -> None:
        """테스트 전 설정."""
        # 임시 디렉토리 생성
        self.temp_dir = tempfile.mkdtemp()
        self.test_dir = Path(self.temp_dir)
        self.checker = IntegrityChecker()
    
    def tearDown(self) -> None:
        """테스트 후 정리."""
        # 임시 디렉토리 정리
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def create_test_file(self, name: str, content: bytes, encoding: str = "utf-8") -> Path:
        """테스트 파일 생성 (바이너리 모드).
        
        Args:
            name: 파일명
            content: 파일 내용 (bytes)
            encoding: 인코딩 (기본값: utf-8)
        
        Returns:
            생성된 파일 경로
        """
        file_path = self.test_dir / name
        file_path.write_bytes(content)
        return file_path
    
    def create_file_record(self, file_path: Path, encoding: str = "utf-8") -> FileRecord:
        """FileRecord 생성.
        
        Args:
            file_path: 파일 경로
            encoding: 인코딩 (기본값: utf-8)
        
        Returns:
            FileRecord 객체
        """
        stat = file_path.stat()
        return FileRecord(
            path=file_path,
            name=file_path.name,
            size=stat.st_size,
            encoding=encoding,
            mtime=stat.st_mtime
        )
    
    def test_check_empty_file(self) -> None:
        """0바이트 파일 탐지 테스트."""
        # 0바이트 파일 생성
        empty_file = self.create_test_file("empty.txt", b"")
        file_record = self.create_file_record(empty_file)
        
        # 무결성 검사
        issues = self.checker.check([file_record])
        
        # 검증
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].code, INTEGRITY_ISSUE_CODE_EMPTY_FILE)
        self.assertEqual(issues[0].severity, "WARN")
        self.assertEqual(issues[0].path, empty_file)
        self.assertIn("빈 파일", issues[0].message)
    
    def test_check_readable_valid_file(self) -> None:
        """정상 파일 읽기 가능 여부 테스트."""
        # 정상 파일 생성
        valid_file = self.create_test_file("valid.txt", "정상 파일 내용".encode("utf-8"))
        file_record = self.create_file_record(valid_file)
        
        # 무결성 검사
        issues = self.checker.check([file_record])
        
        # 검증: 정상 파일은 이슈 없음
        self.assertEqual(len(issues), 0)
    
    def test_check_readable_nonexistent_file(self) -> None:
        """존재하지 않는 파일 테스트."""
        # 존재하지 않는 파일 경로
        nonexistent_file = self.test_dir / "nonexistent.txt"
        file_record = FileRecord(
            path=nonexistent_file,
            name=nonexistent_file.name,
            size=0,
            encoding="utf-8"
        )
        
        # 무결성 검사
        issues = self.checker.check([file_record])
        
        # 검증
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].code, INTEGRITY_ISSUE_CODE_READ_ERROR)
        self.assertEqual(issues[0].severity, "ERROR")
        self.assertIn("존재하지 않음", issues[0].message)
    
    def test_check_decode_sample_valid_utf8(self) -> None:
        """유효한 UTF-8 파일 디코딩 테스트."""
        # UTF-8 파일 생성
        utf8_file = self.create_test_file("utf8.txt", "안녕하세요 UTF-8 테스트".encode("utf-8"))
        file_record = self.create_file_record(utf8_file, encoding="utf-8")
        
        # 무결성 검사
        issues = self.checker.check([file_record])
        
        # 검증: 정상 파일은 이슈 없음
        self.assertEqual(len(issues), 0)
    
    def test_check_decode_sample_invalid_encoding(self) -> None:
        """잘못된 인코딩으로 디코딩 실패 테스트."""
        # UTF-8로 인코딩된 파일을 CP949로 디코딩 시도
        utf8_content = "안녕하세요".encode("utf-8")
        utf8_file = self.create_test_file("utf8_as_cp949.txt", utf8_content)
        # 잘못된 인코딩으로 FileRecord 생성
        file_record = self.create_file_record(utf8_file, encoding="cp949")
        
        # 무결성 검사
        issues = self.checker.check([file_record])
        
        # 검증: 디코딩 오류 발생
        self.assertGreater(len(issues), 0)
        decode_issues = [issue for issue in issues if issue.code == INTEGRITY_ISSUE_CODE_DECODE_ERROR]
        self.assertGreater(len(decode_issues), 0)
        self.assertEqual(decode_issues[0].severity, "ERROR")
        self.assertIn("디코딩 실패", decode_issues[0].message)
    
    def test_check_integration_multiple_files(self) -> None:
        """여러 파일 통합 테스트."""
        # 다양한 파일 생성
        files = [
            ("empty.txt", b"", "utf-8"),  # 0바이트
            ("valid.txt", "정상 파일".encode("utf-8"), "utf-8"),  # 정상
            ("another.txt", "또 다른 파일".encode("utf-8"), "utf-8"),  # 정상
        ]
        
        file_records = []
        for name, content, encoding in files:
            file_path = self.create_test_file(name, content, encoding)
            file_records.append(self.create_file_record(file_path, encoding))
        
        # 무결성 검사
        issues = self.checker.check(file_records)
        
        # 검증: 0바이트 파일만 이슈 발생
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].code, INTEGRITY_ISSUE_CODE_EMPTY_FILE)
    
    def test_check_empty_list(self) -> None:
        """빈 리스트 검사 테스트."""
        issues = self.checker.check([])
        self.assertEqual(len(issues), 0)
    
    def test_check_handles_exception_gracefully(self) -> None:
        """예외 상황에서도 안전하게 처리되는지 테스트."""
        # 정상 파일 생성
        valid_file = self.create_test_file("valid.txt", "정상".encode("utf-8"))
        file_record = self.create_file_record(valid_file)
        
        # 파일 삭제하여 읽기 실패 시뮬레이션
        valid_file.unlink()
        
        # 무결성 검사 (예외 발생해도 계속 진행)
        issues = self.checker.check([file_record])
        
        # 검증: 읽기 오류 이슈 발생
        self.assertGreater(len(issues), 0)
        read_issues = [issue for issue in issues if issue.code == INTEGRITY_ISSUE_CODE_READ_ERROR]
        self.assertGreater(len(read_issues), 0)


class TestIntegrityIssue(unittest.TestCase):
    """IntegrityIssue 테스트 클래스."""
    
    def test_integrity_issue_creation(self) -> None:
        """IntegrityIssue 생성 테스트."""
        from pathlib import Path
        
        path = Path("/test/file.txt")
        issue = IntegrityIssue(
            path=path,
            code="TEST_CODE",
            severity="WARN",
            message="테스트 메시지",
            meta={"key": "value"}
        )
        
        self.assertEqual(issue.path, path)
        self.assertEqual(issue.code, "TEST_CODE")
        self.assertEqual(issue.severity, "WARN")
        self.assertEqual(issue.message, "테스트 메시지")
        self.assertEqual(issue.meta, {"key": "value"})
    
    def test_integrity_issue_default_meta(self) -> None:
        """IntegrityIssue 기본 meta 테스트."""
        from pathlib import Path
        
        path = Path("/test/file.txt")
        issue = IntegrityIssue(
            path=path,
            code="TEST_CODE",
            severity="INFO",
            message="테스트"
        )
        
        self.assertEqual(issue.meta, {})


if __name__ == "__main__":
    unittest.main()

