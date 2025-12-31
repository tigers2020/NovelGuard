"""
무결성 검사 스레드 모듈

백그라운드에서 파일 무결성 검사를 수행하는 스레드 클래스를 제공합니다.
"""

from pathlib import Path
from typing import Optional

from PySide6.QtCore import QThread, Signal

from models.file_record import FileRecord
from checkers.integrity_checker import IntegrityChecker, IntegrityIssue
from utils.logger import get_logger
from utils.exceptions import IntegrityCheckError


class IntegrityCheckerThread(QThread):
    """파일 무결성 검사를 백그라운드에서 수행하는 스레드 클래스.
    
    FileRecord 리스트를 검사하여 무결성 문제를 찾습니다.
    UI 프리징을 방지하기 위해 백그라운드 스레드에서 실행됩니다.
    
    Signals:
        check_finished: 검사가 완료되었을 때 발생
            Args: issues (list[IntegrityIssue]) - 무결성 문제 리스트
        check_error: 검사 중 오류가 발생했을 때 발생
            Args: error_message (str) - 오류 메시지
        progress_updated: 진행 상황이 업데이트되었을 때 발생
            Args: message (str) - 진행 상황 메시지
    """
    
    check_finished = Signal(list)  # IntegrityIssue 리스트
    check_error = Signal(str)  # 오류 메시지
    progress_updated = Signal(str)  # 진행 상황 메시지
    
    def __init__(self, file_records: list[FileRecord]) -> None:
        """무결성 검사 스레드 초기화.
        
        Args:
            file_records: 검사할 FileRecord 리스트
        """
        super().__init__()
        self.file_records = file_records
        self._logger = get_logger("IntegrityCheckerThread")
    
    def run(self) -> None:
        """스레드 실행 메서드.
        
        백그라운드에서 무결성 검사를 수행합니다.
        """
        try:
            self._logger.info(f"무결성 검사 시작: {len(self.file_records)}개 파일")
            
            # 진행 상황 콜백 함수 정의
            def progress_callback(message: str) -> None:
                """진행 상황을 GUI에 전달합니다."""
                self.progress_updated.emit(message)
            
            # 무결성 검사 수행 (진행 상황 콜백 전달)
            checker = IntegrityChecker(progress_callback=progress_callback)
            issues = checker.check(self.file_records)
            
            self._logger.info(f"무결성 검사 완료: {len(issues)}개 문제 발견")
            
            # 결과 전송
            self.check_finished.emit(issues)
            
        except IntegrityCheckError as e:
            error_msg = f"무결성 검사 오류: {str(e)}"
            self._logger.error(error_msg, exc_info=True)
            self.check_error.emit(error_msg)
        except Exception as e:
            error_msg = f"예상치 못한 무결성 검사 오류: {str(e)}"
            self._logger.error(error_msg, exc_info=True)
            self.check_error.emit(error_msg)

