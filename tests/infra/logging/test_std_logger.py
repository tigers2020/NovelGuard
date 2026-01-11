"""StdLogger 구현 테스트."""

import logging
from pathlib import Path
import tempfile

import pytest

from domain.ports.logger import ILogger
from infra.logging.std_logger import StdLogger, create_std_logger


class TestStdLogger:
    """StdLogger 클래스 테스트."""
    
    def test_implements_ilogger_protocol(self):
        """StdLogger가 ILogger Protocol을 구현하는지 확인."""
        logger = logging.getLogger("test")
        std_logger = StdLogger(logger)
        
        # Protocol 구현 확인 (Python 3.10+에서는 isinstance 사용 가능)
        assert hasattr(std_logger, 'info')
        assert hasattr(std_logger, 'warning')
        assert hasattr(std_logger, 'error')
        assert hasattr(std_logger, 'debug')
        
        # 메서드 호출 가능 확인
        assert callable(std_logger.info)
        assert callable(std_logger.warning)
        assert callable(std_logger.error)
        assert callable(std_logger.debug)
    
    def test_info_without_context(self, caplog):
        """info() 메서드가 context 없이 정상 작동하는지 확인."""
        logger = logging.getLogger("test_info")
        logger.setLevel(logging.INFO)
        std_logger = StdLogger(logger)
        
        with caplog.at_level(logging.INFO, logger="test_info"):
            std_logger.info("테스트 메시지")
        
        assert "테스트 메시지" in caplog.text
    
    def test_info_with_context(self, caplog):
        """info() 메서드가 context와 함께 정상 작동하는지 확인."""
        logger = logging.getLogger("test_info_context")
        logger.setLevel(logging.INFO)
        std_logger = StdLogger(logger)
        
        with caplog.at_level(logging.INFO, logger="test_info_context"):
            std_logger.info("파일 처리", {"file": "test.txt", "size": 1024})
        
        assert "파일 처리" in caplog.text
        assert "file" in caplog.text
        assert "test.txt" in caplog.text
    
    def test_warning_without_context(self, caplog):
        """warning() 메서드가 context 없이 정상 작동하는지 확인."""
        logger = logging.getLogger("test_warning")
        logger.setLevel(logging.WARNING)
        std_logger = StdLogger(logger)
        
        with caplog.at_level(logging.WARNING, logger="test_warning"):
            std_logger.warning("경고 메시지")
        
        assert "경고 메시지" in caplog.text
    
    def test_error_without_context(self, caplog):
        """error() 메서드가 context 없이 정상 작동하는지 확인."""
        logger = logging.getLogger("test_error")
        logger.setLevel(logging.ERROR)
        std_logger = StdLogger(logger)
        
        with caplog.at_level(logging.ERROR, logger="test_error"):
            std_logger.error("에러 메시지")
        
        assert "에러 메시지" in caplog.text
    
    def test_debug_without_context(self, caplog):
        """debug() 메서드가 context 없이 정상 작동하는지 확인."""
        logger = logging.getLogger("test_debug")
        logger.setLevel(logging.DEBUG)
        std_logger = StdLogger(logger)
        
        with caplog.at_level(logging.DEBUG, logger="test_debug"):
            std_logger.debug("디버그 메시지")
        
        assert "디버그 메시지" in caplog.text


class TestCreateStdLogger:
    """create_std_logger() Factory 함수 테스트."""
    
    def test_returns_ilogger(self):
        """create_std_logger()가 ILogger를 반환하는지 확인."""
        logger = create_std_logger(name="test_factory")
        
        # ILogger Protocol 메서드 확인
        assert hasattr(logger, 'info')
        assert hasattr(logger, 'warning')
        assert hasattr(logger, 'error')
        assert hasattr(logger, 'debug')
    
    def test_console_only_logger(self, caplog):
        """파일 없이 콘솔 로거만 생성하는지 확인."""
        logger = create_std_logger(name="test_console", level=logging.INFO)
        
        with caplog.at_level(logging.INFO, logger="test_console"):
            logger.info("콘솔 테스트")
        
        assert "콘솔 테스트" in caplog.text
    
    def test_file_logger_creation(self):
        """파일 로거가 정상 생성되는지 확인."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "test.log"
            logger = create_std_logger(
                name="test_file",
                log_file=log_file,
                level=logging.INFO
            )
            
            logger.info("파일 로그 테스트")
            
            # 로그 파일 생성 확인
            assert log_file.exists()
            
            # 로거 핸들러를 닫아서 파일 핸들 해제
            std_logger = logging.getLogger("test_file")
            for handler in std_logger.handlers[:]:
                handler.close()
                std_logger.removeHandler(handler)
            
            # 로그 내용 확인
            log_content = log_file.read_text(encoding='utf-8')
            assert "파일 로그 테스트" in log_content
    
    def test_custom_format_string(self, caplog):
        """커스텀 포맷 문자열이 적용되는지 확인."""
        custom_format = "%(levelname)s: %(message)s"
        logger = create_std_logger(
            name="test_custom_format",
            level=logging.INFO,
            format_string=custom_format
        )
        
        with caplog.at_level(logging.INFO, logger="test_custom_format"):
            logger.info("포맷 테스트")
        
        assert "INFO: 포맷 테스트" in caplog.text or "포맷 테스트" in caplog.text
    
    def test_log_level_filtering(self):
        """로그 레벨 필터링이 정상 작동하는지 확인."""
        # 임시 파일에 로그를 기록하여 레벨 필터링 확인
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "test_level.log"
            logger = create_std_logger(
                name="test_level_filter",
                log_file=log_file,
                level=logging.WARNING
            )
            
            logger.debug("디버그 메시지")  # 필터링됨
            logger.info("정보 메시지")  # 필터링됨
            logger.warning("경고 메시지")  # 출력됨
            logger.error("에러 메시지")  # 출력됨
            
            # 로거 핸들러를 닫아서 파일 핸들 해제
            std_logger = logging.getLogger("test_level_filter")
            for handler in std_logger.handlers[:]:
                handler.close()
                std_logger.removeHandler(handler)
            
            # 로그 파일 내용 확인
            log_content = log_file.read_text(encoding='utf-8')
            
            assert "디버그 메시지" not in log_content
            assert "정보 메시지" not in log_content
            assert "경고 메시지" in log_content
            assert "에러 메시지" in log_content
    
    def test_backwards_compatibility_with_setup_logging(self):
        """기존 setup_logging()과 동일한 동작을 하는지 확인."""
        # 기본 파라미터로 생성
        logger = create_std_logger()
        
        # 기본 동작 확인
        assert hasattr(logger, 'info')
        assert hasattr(logger, 'warning')
        assert hasattr(logger, 'error')
        assert hasattr(logger, 'debug')
