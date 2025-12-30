"""
파일 스캐너 테스트

FileScannerThread의 동작을 테스트합니다.
"""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from PySide6.QtCore import QCoreApplication

# 프로젝트 루트를 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from models.file_record import FileRecord
from scanners.file_scanner import FileScannerThread


class TestFileScannerThread(unittest.TestCase):
    """FileScannerThread 테스트 클래스."""
    
    @classmethod
    def setUpClass(cls) -> None:
        """테스트 클래스 초기화."""
        # QCoreApplication이 없으면 생성
        if not QCoreApplication.instance():
            cls.app = QCoreApplication([])
        else:
            cls.app = QCoreApplication.instance()
    
    def setUp(self) -> None:
        """테스트 전 설정."""
        # 임시 디렉토리 생성
        self.temp_dir = tempfile.mkdtemp()
        self.test_dir = Path(self.temp_dir)
    
    def tearDown(self) -> None:
        """테스트 후 정리."""
        # 임시 디렉토리 정리
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def create_test_file(self, name: str, content: str = "test content") -> Path:
        """테스트 파일 생성."""
        file_path = self.test_dir / name
        file_path.write_text(content, encoding="utf-8")
        return file_path
    
    def test_scanner_initialization(self) -> None:
        """스캐너 초기화 테스트."""
        scanner = FileScannerThread(self.test_dir)
        
        self.assertEqual(scanner.folder_path, self.test_dir)
        self.assertFalse(scanner.detect_encoding)
        self.assertEqual(scanner._batch_size, 20)
    
    def test_scanner_with_encoding_detection(self) -> None:
        """인코딩 감지 옵션 테스트."""
        scanner = FileScannerThread(self.test_dir, detect_encoding=True)
        
        self.assertTrue(scanner.detect_encoding)
    
    def test_scan_nonexistent_folder(self) -> None:
        """존재하지 않는 폴더 스캔 테스트."""
        nonexistent = Path("/nonexistent/path/12345")
        scanner = FileScannerThread(nonexistent)
        
        # 시그널 모니터링
        error_messages = []
        scanner.scan_error.connect(lambda msg: error_messages.append(msg))
        
        scanner.run()
        
        self.assertGreater(len(error_messages), 0)
        self.assertIn("존재하지 않습니다", error_messages[0])
    
    def test_scan_empty_folder(self) -> None:
        """빈 폴더 스캔 테스트."""
        scanner = FileScannerThread(self.test_dir)
        
        # 시그널 모니터링
        finished_counts = []
        scanner.scan_finished.connect(lambda count: finished_counts.append(count))
        
        scanner.run()
        
        self.assertEqual(len(finished_counts), 1)
        self.assertEqual(finished_counts[0], 0)
    
    def test_scan_single_file(self) -> None:
        """단일 파일 스캔 테스트."""
        self.create_test_file("test.txt", "test content")
        
        scanner = FileScannerThread(self.test_dir, detect_encoding=False)
        
        # 시그널 모니터링
        batches = []
        finished_counts = []
        
        scanner.files_found_batch.connect(lambda records: batches.append(records))
        scanner.scan_finished.connect(lambda count: finished_counts.append(count))
        
        scanner.run()
        
        self.assertEqual(len(finished_counts), 1)
        self.assertEqual(finished_counts[0], 1)
        self.assertGreater(len(batches), 0)
        
        # 배치에 파일이 있는지 확인
        all_records = []
        for batch in batches:
            all_records.extend(batch)
        
        self.assertEqual(len(all_records), 1)
        self.assertIsInstance(all_records[0], FileRecord)
        self.assertEqual(all_records[0].name, "test.txt")
    
    def test_scan_multiple_files(self) -> None:
        """여러 파일 스캔 테스트."""
        for i in range(5):
            self.create_test_file(f"test_{i}.txt", f"content {i}")
        
        scanner = FileScannerThread(self.test_dir, detect_encoding=False)
        
        # 시그널 모니터링
        batches = []
        finished_counts = []
        
        scanner.files_found_batch.connect(lambda records: batches.append(records))
        scanner.scan_finished.connect(lambda count: finished_counts.append(count))
        
        scanner.run()
        
        self.assertEqual(len(finished_counts), 1)
        self.assertEqual(finished_counts[0], 5)
        
        # 모든 파일이 발견되었는지 확인
        all_records = []
        for batch in batches:
            all_records.extend(batch)
        
        self.assertEqual(len(all_records), 5)
        self.assertEqual(set(r.name for r in all_records), 
                        {f"test_{i}.txt" for i in range(5)})
    
    def test_scan_nested_folders(self) -> None:
        """중첩 폴더 스캔 테스트."""
        subdir = self.test_dir / "subdir"
        subdir.mkdir()
        
        self.create_test_file("root.txt", "root content")
        (subdir / "nested.txt").write_text("nested content", encoding="utf-8")
        
        scanner = FileScannerThread(self.test_dir, detect_encoding=False)
        
        # 시그널 모니터링
        batches = []
        finished_counts = []
        
        scanner.files_found_batch.connect(lambda records: batches.append(records))
        scanner.scan_finished.connect(lambda count: finished_counts.append(count))
        
        scanner.run()
        
        self.assertEqual(len(finished_counts), 1)
        self.assertEqual(finished_counts[0], 2)
        
        # 모든 파일이 발견되었는지 확인
        all_records = []
        for batch in batches:
            all_records.extend(batch)
        
        self.assertEqual(len(all_records), 2)
        names = {r.name for r in all_records}
        self.assertIn("root.txt", names)
        self.assertIn("nested.txt", names)
    
    def test_scan_only_txt_files(self) -> None:
        """.txt 파일만 스캔하는지 테스트."""
        self.create_test_file("test.txt", "txt content")
        (self.test_dir / "test.py").write_text("python code", encoding="utf-8")
        (self.test_dir / "test.md").write_text("markdown", encoding="utf-8")
        
        scanner = FileScannerThread(self.test_dir, detect_encoding=False)
        
        # 시그널 모니터링
        batches = []
        finished_counts = []
        
        scanner.files_found_batch.connect(lambda records: batches.append(records))
        scanner.scan_finished.connect(lambda count: finished_counts.append(count))
        
        scanner.run()
        
        self.assertEqual(len(finished_counts), 1)
        self.assertEqual(finished_counts[0], 1)  # .txt 파일만
        
        # .txt 파일만 발견되었는지 확인
        all_records = []
        for batch in batches:
            all_records.extend(batch)
        
        self.assertEqual(len(all_records), 1)
        self.assertEqual(all_records[0].name, "test.txt")
    
    def test_file_record_creation(self) -> None:
        """FileRecord 생성 테스트."""
        file_path = self.create_test_file("test.txt", "test content")
        file_size = file_path.stat().st_size
        
        scanner = FileScannerThread(self.test_dir, detect_encoding=False)
        
        # 시그널 모니터링
        batches = []
        scanner.files_found_batch.connect(lambda records: batches.append(records))
        
        scanner.run()
        
        # FileRecord가 올바르게 생성되었는지 확인
        all_records = []
        for batch in batches:
            all_records.extend(batch)
        
        self.assertEqual(len(all_records), 1)
        record = all_records[0]
        
        self.assertEqual(record.path, file_path)
        self.assertEqual(record.name, "test.txt")
        self.assertEqual(record.size, file_size)
        self.assertEqual(record.encoding, "-")  # 인코딩 감지 비활성화


if __name__ == "__main__":
    unittest.main()

