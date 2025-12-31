"""
파일 스캐너 모듈

백그라운드에서 파일을 스캔하는 스레드 클래스를 제공합니다.
"""

from pathlib import Path
from typing import Optional
import logging

from PySide6.QtCore import QThread, Signal

from models.file_record import FileRecord
from utils.logger import get_logger
from utils.exceptions import FileScanError
from utils.constants import SCAN_BATCH_SIZE
from scanners.file_record_builder import FileRecordBuilder


class FileScannerThread(QThread):
    """파일 스캔을 백그라운드에서 수행하는 스레드 클래스.
    
    폴더 내 .txt 파일을 재귀적으로 스캔하여 FileRecord 객체를 생성합니다.
    배치 단위로 결과를 전송하여 UI 반응성을 유지합니다.
    
    Signals:
        files_found_batch: 파일 정보를 배치 단위로 전송
            Args: file_records (list[FileRecord]) - 파일 정보 리스트
        scan_finished: 스캔이 완료되었을 때 발생
            Args: total_count (int) - 발견된 파일 총 개수
        scan_error: 스캔 중 오류가 발생했을 때 발생
            Args: error_message (str) - 오류 메시지
    """
    
    files_found_batch = Signal(list)  # FileRecord 리스트 (배치)
    scan_finished = Signal(int)  # 총 파일 개수
    scan_error = Signal(str)  # 오류 메시지
    
    def __init__(self, folder_path: Path, detect_encoding: bool = True) -> None:
        """파일 스캐너 스레드 초기화.
        
        Args:
            folder_path: 스캔할 폴더 경로
            detect_encoding: 인코딩 감지 여부 (기본값: True, 정책 변경: 스캔 단계에서 encoding 확정)
        """
        super().__init__()
        self.folder_path = folder_path
        self.detect_encoding = detect_encoding
        self._batch_size = SCAN_BATCH_SIZE
        self._logger = get_logger("FileScanner")
        self._builder = FileRecordBuilder()
    
    def run(self) -> None:
        """스레드 실행 메서드.
        
        폴더 내 .txt 파일을 재귀적으로 스캔합니다.
        최적화: 순차 처리, 빠른 스캔, 인코딩 감지는 선택적.
        """
        try:
            self._logger.info(f"파일 스캔 시작: {self.folder_path}")
            
            if not self.folder_path.exists():
                error_msg = f"선택한 폴더가 존재하지 않습니다: {self.folder_path}"
                self._logger.error(error_msg)
                self.scan_error.emit("선택한 폴더가 존재하지 않습니다.")
                return
            
            if not self.folder_path.is_dir():
                error_msg = f"선택한 경로가 폴더가 아닙니다: {self.folder_path}"
                self._logger.error(error_msg)
                self.scan_error.emit("선택한 경로가 폴더가 아닙니다.")
                return
            
            # 파일 스캔 - 제너레이터로 처리하여 메모리 효율성 향상
            # O(1) 메모리 사용 (리스트 변환 대신)
            txt_files = self.folder_path.rglob("*.txt")
            
            # 파일 정보 수집
            file_count = 0
            batch: list[FileRecord] = []
            skipped_count = 0
            
            for file_path in txt_files:
                # 스레드 중단 요청 확인
                if self.isInterruptionRequested():
                    self._logger.info("스캔 중단 요청됨")
                    return
                
                try:
                    # FileRecord 생성 (빌더 사용)
                    file_record = self._builder.build(file_path, detect_encoding=self.detect_encoding)
                    
                    batch.append(file_record)
                    file_count += 1
                    
                    # 배치가 가득 차면 전송 (UI 반응성 향상)
                    if len(batch) >= self._batch_size:
                        self.files_found_batch.emit(batch)
                        batch = []
                    
                except (OSError, PermissionError) as e:
                    # 파일 접근 오류는 스킵하고 로그 기록
                    skipped_count += 1
                    self._logger.warning(f"파일 접근 오류 (스킵): {file_path} - {e}")
                    continue
                except ValueError as e:
                    # FileRecord 검증 실패
                    skipped_count += 1
                    self._logger.warning(f"파일 정보 검증 실패 (스킵): {file_path} - {e}")
                    continue
                except Exception as e:
                    # 예상치 못한 오류는 스킵하되 계속 진행
                    skipped_count += 1
                    self._logger.error(f"예상치 못한 오류 (스킵): {file_path} - {e}", exc_info=True)
                    continue
            
            # 남은 배치 전송
            if batch:
                self.files_found_batch.emit(batch)
            
            self._logger.info(
                f"파일 스캔 완료: {file_count}개 파일 발견, {skipped_count}개 파일 스킵"
            )
            self.scan_finished.emit(file_count)
            
        except FileNotFoundError as e:
            error_msg = f"폴더를 찾을 수 없습니다: {self.folder_path}"
            self._logger.error(error_msg, exc_info=True)
            self.scan_error.emit("선택한 폴더를 찾을 수 없습니다.")
        except PermissionError as e:
            error_msg = f"폴더 접근 권한이 없습니다: {self.folder_path}"
            self._logger.error(error_msg, exc_info=True)
            self.scan_error.emit("폴더 접근 권한이 없습니다.")
        except FileScanError as e:
            error_msg = f"파일 스캔 오류: {e}"
            self._logger.error(error_msg, exc_info=True)
            self.scan_error.emit(f"스캔 중 오류 발생: {str(e)}")
        except Exception as e:
            error_msg = f"예상치 못한 스캔 오류: {e}"
            self._logger.error(error_msg, exc_info=True)
            self.scan_error.emit(f"스캔 중 오류 발생: {str(e)}")
    

