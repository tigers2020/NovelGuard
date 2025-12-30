"""
중복 분석 스레드 모듈

백그라운드에서 중복 파일 분석을 수행하는 스레드 클래스를 제공합니다.
"""

from pathlib import Path
from typing import Optional
import logging

from PySide6.QtCore import QThread, Signal

from models.file_record import FileRecord
from analyzers.duplicate_analyzer import DuplicateAnalyzer
from utils.logger import get_logger
from utils.exceptions import DuplicateAnalysisError


class DuplicateAnalyzerThread(QThread):
    """중복 파일 분석을 백그라운드에서 수행하는 스레드 클래스.
    
    FileRecord 리스트를 분석하여 중복 그룹을 찾습니다.
    UI 프리징을 방지하기 위해 백그라운드 스레드에서 실행됩니다.
    
    Signals:
        analysis_finished: 분석이 완료되었을 때 발생
            Args: duplicate_groups (list[list[FileRecord]]) - 중복 그룹 리스트
        analysis_error: 분석 중 오류가 발생했을 때 발생
            Args: error_message (str) - 오류 메시지
        progress_updated: 진행 상황이 업데이트되었을 때 발생 (선택적)
            Args: message (str) - 진행 상황 메시지
    """
    
    analysis_finished = Signal(list)  # 중복 그룹 리스트
    analysis_error = Signal(str)  # 오류 메시지
    progress_updated = Signal(str)  # 진행 상황 메시지
    
    def __init__(self, file_records: list[FileRecord]) -> None:
        """중복 분석 스레드 초기화.
        
        Args:
            file_records: 분석할 FileRecord 리스트
        """
        super().__init__()
        self.file_records = file_records
        self._logger = get_logger("DuplicateAnalyzerThread")
    
    def run(self) -> None:
        """스레드 실행 메서드.
        
        백그라운드에서 중복 분석을 수행합니다.
        """
        # #region agent log
        import json
        import time
        try:
            with open(r"f:\Python_Projects\NovelGuard\.cursor\debug.log", "a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "sessionId": "debug-session",
                    "runId": "run1",
                    "hypothesisId": "A",
                    "location": "duplicate_analyzer_thread.py:run",
                    "message": "Thread run() started",
                    "data": {"file_count": len(self.file_records), "thread_id": id(self)},
                    "timestamp": int(time.time() * 1000)
                }) + "\n")
        except: pass
        # #endregion
        
        try:
            self._logger.info(f"중복 분석 시작: {len(self.file_records)}개 파일")
            self.progress_updated.emit("중복 분석 중...")
            
            # #region agent log
            try:
                with open(r"f:\Python_Projects\NovelGuard\.cursor\debug.log", "a", encoding="utf-8") as f:
                    f.write(json.dumps({
                        "sessionId": "debug-session",
                        "runId": "run1",
                        "hypothesisId": "B",
                        "location": "duplicate_analyzer_thread.py:run",
                        "message": "Before analyzer.analyze()",
                        "data": {"timestamp": int(time.time() * 1000)},
                        "timestamp": int(time.time() * 1000)
                    }) + "\n")
            except: pass
            # #endregion
            
            # 중복 분석 수행
            analyzer = DuplicateAnalyzer()
            duplicate_groups = analyzer.analyze(self.file_records)
            
            # #region agent log
            try:
                with open(r"f:\Python_Projects\NovelGuard\.cursor\debug.log", "a", encoding="utf-8") as f:
                    f.write(json.dumps({
                        "sessionId": "debug-session",
                        "runId": "run1",
                        "hypothesisId": "B",
                        "location": "duplicate_analyzer_thread.py:run",
                        "message": "After analyzer.analyze()",
                        "data": {"groups_found": len(duplicate_groups), "timestamp": int(time.time() * 1000)},
                        "timestamp": int(time.time() * 1000)
                    }) + "\n")
            except: pass
            # #endregion
            
            self._logger.info(f"중복 분석 완료: {len(duplicate_groups)}개 그룹 발견")
            self.progress_updated.emit("중복 분석 완료")
            
            # #region agent log
            try:
                with open(r"f:\Python_Projects\NovelGuard\.cursor\debug.log", "a", encoding="utf-8") as f:
                    f.write(json.dumps({
                        "sessionId": "debug-session",
                        "runId": "run1",
                        "hypothesisId": "C",
                        "location": "duplicate_analyzer_thread.py:run",
                        "message": "Before emit analysis_finished",
                        "data": {"timestamp": int(time.time() * 1000)},
                        "timestamp": int(time.time() * 1000)
                    }) + "\n")
            except: pass
            # #endregion
            
            # 결과 전송
            self.analysis_finished.emit(duplicate_groups)
            
            # #region agent log
            try:
                with open(r"f:\Python_Projects\NovelGuard\.cursor\debug.log", "a", encoding="utf-8") as f:
                    f.write(json.dumps({
                        "sessionId": "debug-session",
                        "runId": "run1",
                        "hypothesisId": "C",
                        "location": "duplicate_analyzer_thread.py:run",
                        "message": "After emit analysis_finished",
                        "data": {"timestamp": int(time.time() * 1000)},
                        "timestamp": int(time.time() * 1000)
                    }) + "\n")
            except: pass
            # #endregion
            
        except DuplicateAnalysisError as e:
            error_msg = f"중복 분석 오류: {str(e)}"
            self._logger.error(error_msg, exc_info=True)
            self.analysis_error.emit(error_msg)
        except Exception as e:
            error_msg = f"예상치 못한 중복 분석 오류: {str(e)}"
            self._logger.error(error_msg, exc_info=True)
            self.analysis_error.emit(error_msg)

