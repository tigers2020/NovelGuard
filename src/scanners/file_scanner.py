"""
파일 스캐너 모듈

백그라운드에서 파일을 스캔하는 스레드 클래스를 제공합니다.
"""

from pathlib import Path
from typing import Optional
import logging

from PySide6.QtCore import QThread, Signal
import charset_normalizer

from models.file_record import FileRecord
from utils.logger import get_logger
from utils.exceptions import FileScanError, FileEncodingError
from utils.filename_parser import extract_title, extract_normalized_title, extract_episode_range


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
    
    def __init__(self, folder_path: Path, detect_encoding: bool = False) -> None:
        """파일 스캐너 스레드 초기화.
        
        Args:
            folder_path: 스캔할 폴더 경로
            detect_encoding: 인코딩 감지 여부 (기본값: False, 속도 우선)
        """
        super().__init__()
        self.folder_path = folder_path
        self.detect_encoding = detect_encoding
        self._batch_size = 20  # 배치 크기 (UI 반응성 향상)
        self._logger = get_logger("FileScanner")
    
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
                    # 파일 크기 (O(1) - 메타데이터만 읽음)
                    file_size = file_path.stat().st_size
                    
                    # 인코딩 감지 (선택적)
                    encoding = "-"
                    if self.detect_encoding:
                        try:
                            encoding = self._detect_encoding_optimized(file_path)
                        except FileEncodingError as e:
                            self._logger.warning(f"인코딩 감지 실패: {file_path} - {e}")
                            encoding = "N/A"
                    
                    # 파일명 파싱 (제목, 정규화 제목, 회차 범위)
                    title = extract_title(file_path.name)
                    normalized_title = extract_normalized_title(file_path.name)
                    episode_range = extract_episode_range(file_path.name)
                    
                    # FileRecord 생성
                    file_record = FileRecord(
                        path=file_path,
                        name=file_path.name,
                        size=file_size,
                        encoding=encoding,
                        title=title if title else None,
                        normalized_title=normalized_title if normalized_title else None,
                        episode_range=episode_range,
                    )
                    
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
    
    def _detect_encoding_optimized(self, file_path: Path) -> str:
        """인코딩을 최적화된 방식으로 감지합니다.
        
        전체 파일을 읽지 않고 샘플만 읽어서 인코딩을 감지합니다.
        시간 복잡도: O(1) - 최대 32KB만 읽음 (더 작은 샘플로 최적화)
        
        Args:
            file_path: 감지할 파일 경로
            
        Returns:
            감지된 인코딩 이름 또는 "Unknown"/"N/A"/"Empty"
            
        Raises:
            FileEncodingError: 인코딩 감지 중 오류 발생 시
        """
        # 최대 샘플 크기: 32KB (인코딩 감지에 충분하며 더 빠름)
        MAX_SAMPLE_SIZE = 32 * 1024
        
        try:
            with open(file_path, "rb") as f:
                # 파일 크기 확인
                file_size = file_path.stat().st_size
                
                if file_size == 0:
                    return "Empty"
                
                # 샘플만 읽기 (O(1) 상수 시간)
                sample_size = min(file_size, MAX_SAMPLE_SIZE)
                raw_data = f.read(sample_size)
                
                if not raw_data:
                    return "Unknown"
                
                # charset_normalizer는 샘플로도 정확하게 감지 가능
                detected = charset_normalizer.detect(raw_data)
                if detected and detected.get("encoding"):
                    encoding = detected["encoding"]
                    self._logger.debug(f"인코딩 감지 성공: {file_path} - {encoding}")
                    return encoding
                
                return "Unknown"
                
        except (OSError, PermissionError) as e:
            self._logger.warning(f"인코딩 감지 중 파일 접근 오류: {file_path} - {e}")
            raise FileEncodingError(f"파일 접근 오류: {file_path}") from e
        except Exception as e:
            self._logger.error(f"인코딩 감지 중 예상치 못한 오류: {file_path} - {e}", exc_info=True)
            raise FileEncodingError(f"인코딩 감지 실패: {file_path}") from e

