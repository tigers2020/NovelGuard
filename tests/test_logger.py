"""
로깅 유틸리티 테스트

로거 설정 및 동작을 테스트합니다.
"""

import logging
import sys
import tempfile
import unittest
from pathlib import Path

# 프로젝트 루트를 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from utils.logger import setup_logger, get_logger


class TestLogger(unittest.TestCase):
    """로깅 유틸리티 테스트 클래스."""
    
    def setUp(self) -> None:
        """테스트 전 설정."""
        # 기존 핸들러 제거
        for logger_name in ["NovelGuard", "NovelGuard.Test", "TestLogger"]:
            logger = logging.getLogger(logger_name)
            logger.handlers.clear()
            logger.setLevel(logging.NOTSET)
    
    def tearDown(self) -> None:
        """테스트 후 정리."""
        # 테스트 후 핸들러 제거 및 닫기
        for logger_name in ["NovelGuard", "NovelGuard.Test", "TestLogger"]:
            logger = logging.getLogger(logger_name)
            # 핸들러 닫기
            for handler in logger.handlers[:]:
                handler.close()
                logger.removeHandler(handler)
            logger.handlers.clear()
    
    def test_setup_logger_creates_logger(self) -> None:
        """로거 생성 테스트."""
        logger = setup_logger("TestLogger")
        
        self.assertIsInstance(logger, logging.Logger)
        self.assertEqual(logger.name, "TestLogger")
        self.assertEqual(logger.level, logging.INFO)
    
    def test_setup_logger_has_console_handler(self) -> None:
        """콘솔 핸들러 존재 테스트."""
        logger = setup_logger("TestLogger")
        
        handlers = [h for h in logger.handlers if isinstance(h, logging.StreamHandler)]
        self.assertGreater(len(handlers), 0)
    
    def test_setup_logger_with_file_handler(self) -> None:
        """파일 핸들러 설정 테스트."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "test.log"
            logger = setup_logger("TestLogger", log_file=log_file)
            
            try:
                # 파일 핸들러 확인
                file_handlers = [h for h in logger.handlers if isinstance(h, logging.FileHandler)]
                self.assertGreater(len(file_handlers), 0)
                
                # 로그 파일이 생성되었는지 확인
                self.assertTrue(log_file.exists())
            finally:
                # 핸들러 닫기
                for handler in logger.handlers[:]:
                    handler.close()
                    logger.removeHandler(handler)
    
    def test_setup_logger_returns_existing_logger(self) -> None:
        """기존 로거 반환 테스트."""
        logger1 = setup_logger("TestLogger")
        logger2 = setup_logger("TestLogger")
        
        # 같은 로거 객체 반환
        self.assertIs(logger1, logger2)
    
    def test_setup_logger_custom_level(self) -> None:
        """커스텀 로그 레벨 설정 테스트."""
        logger = setup_logger("TestLogger", level=logging.DEBUG)
        
        self.assertEqual(logger.level, logging.DEBUG)
    
    def test_get_logger_with_name(self) -> None:
        """이름이 있는 로거 가져오기 테스트."""
        logger = get_logger("Test")
        
        self.assertIsInstance(logger, logging.Logger)
        self.assertEqual(logger.name, "NovelGuard.Test")
    
    def test_get_logger_without_name(self) -> None:
        """이름이 없는 로거 가져오기 테스트."""
        logger = get_logger()
        
        self.assertIsInstance(logger, logging.Logger)
        self.assertEqual(logger.name, "NovelGuard")
    
    def test_logger_logs_messages(self) -> None:
        """로거 메시지 기록 테스트."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "test.log"
            logger = setup_logger("TestLogger", log_file=log_file, level=logging.DEBUG)
            
            try:
                logger.info("테스트 정보 메시지")
                logger.warning("테스트 경고 메시지")
                logger.error("테스트 오류 메시지")
                
                # 핸들러 플러시
                for handler in logger.handlers:
                    handler.flush()
                
                # 로그 파일 내용 확인
                self.assertTrue(log_file.exists())
                content = log_file.read_text(encoding="utf-8")
                self.assertIn("테스트 정보 메시지", content)
                self.assertIn("테스트 경고 메시지", content)
                self.assertIn("테스트 오류 메시지", content)
            finally:
                # 핸들러 닫기
                for handler in logger.handlers[:]:
                    handler.close()
                    logger.removeHandler(handler)
    
    def test_logger_file_handler_creates_directory(self) -> None:
        """로그 파일 핸들러가 디렉토리를 생성하는지 테스트."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "subdir" / "test.log"
            logger = setup_logger("TestLogger", log_file=log_file)
            
            try:
                # 디렉토리가 생성되었는지 확인
                self.assertTrue(log_file.parent.exists())
                self.assertTrue(log_file.exists())
            finally:
                # 핸들러 닫기
                for handler in logger.handlers[:]:
                    handler.close()
                    logger.removeHandler(handler)


if __name__ == "__main__":
    unittest.main()

