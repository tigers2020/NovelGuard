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
from analyzers.duplicate_group import DuplicateGroup
from utils.logger import get_logger
from utils.exceptions import DuplicateAnalysisError


class DuplicateAnalyzerThread(QThread):
    """중복 파일 분석을 백그라운드에서 수행하는 스레드 클래스.
    
    FileRecord 리스트를 분석하여 중복 그룹을 찾습니다.
    UI 프리징을 방지하기 위해 백그라운드 스레드에서 실행됩니다.
    
    Signals:
        analysis_finished: 분석이 완료되었을 때 발생
            Args: duplicate_groups (list[list[FileRecord]]) - 중복 그룹 리스트
        analysis_finished_with_groups: 분석이 완료되었을 때 발생 (DuplicateGroup 정보 포함)
            Args: duplicate_groups (list[DuplicateGroup]) - 중복 그룹 리스트 (keep_file 정보 포함)
        analysis_error: 분석 중 오류가 발생했을 때 발생
            Args: error_message (str) - 오류 메시지
        progress_updated: 진행 상황이 업데이트되었을 때 발생 (선택적)
            Args: message (str) - 진행 상황 메시지
    """
    
    analysis_finished = Signal(list)  # 중복 그룹 리스트 (기존 호환성)
    analysis_finished_with_groups = Signal(list)  # DuplicateGroup 리스트 (keep_file 정보 포함)
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
        try:
            self._logger.info(f"중복 분석 시작: {len(self.file_records)}개 파일")
            self.progress_updated.emit("중복 분석 시작...")
            
            # 진행 상황 콜백 함수 정의
            def progress_callback(message: str) -> None:
                """진행 상황을 GUI에 전달합니다."""
                self.progress_updated.emit(message)
            
            # 중복 분석 수행
            analyzer = DuplicateAnalyzer(progress_callback=progress_callback)
            
            # keep_file 정보를 포함한 그룹 정보 가져오기
            duplicate_groups_with_info = analyzer.analyze_with_groups(self.file_records)
            
            # 기존 호환성을 위해 list[list[FileRecord]] 형태도 생성
            duplicate_groups_simple = [group.members for group in duplicate_groups_with_info]
            
            self._logger.info(f"중복 분석 완료: {len(duplicate_groups_with_info)}개 그룹 발견")
            # analyze_with_groups() 내부에서 이미 최종 진행 상황을 emit하므로 여기서는 생략
            
            # 결과 전송 (기존 호환성)
            self.analysis_finished.emit(duplicate_groups_simple)
            # keep_file 정보 포함 그룹 전송
            self.analysis_finished_with_groups.emit(duplicate_groups_with_info)
            
        except DuplicateAnalysisError as e:
            error_msg = f"중복 분석 오류: {str(e)}"
            self._logger.error(error_msg, exc_info=True)
            self.analysis_error.emit(error_msg)
        except Exception as e:
            error_msg = f"예상치 못한 중복 분석 오류: {str(e)}"
            self._logger.error(error_msg, exc_info=True)
            self.analysis_error.emit(error_msg)

