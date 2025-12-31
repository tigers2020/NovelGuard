"""
FileRecord 빌더 모듈

파일 경로와 메타데이터로부터 FileRecord를 생성하는 기능을 제공합니다.
"""

from pathlib import Path
from typing import Optional

from models.file_record import FileRecord
from utils.logger import get_logger
from utils.exceptions import FileEncodingError
from utils.encoding_detector import detect_encoding_path
from utils.constants import (
    DEFAULT_ENCODING,
    ENCODING_UNKNOWN,
    ENCODING_EMPTY,
    ENCODING_NA,
    ENCODING_NOT_DETECTED,
)
from utils.filename_parser import (
    extract_title, 
    extract_normalized_title, 
    extract_episode_range,
    extract_base_title,
    extract_episode_end,
    extract_variant_flags
)


class FileRecordBuilder:
    """FileRecord 빌더 클래스.
    
    파일 경로와 메타데이터로부터 FileRecord를 생성합니다.
    파일명 파싱, 인코딩 감지 등의 로직을 캡슐화합니다.
    
    Attributes:
        _logger: 로거 인스턴스
    """
    
    def __init__(self) -> None:
        """FileRecordBuilder 초기화."""
        self._logger = get_logger("FileRecordBuilder")
    
    def build(
        self,
        file_path: Path,
        detect_encoding: bool = True
    ) -> FileRecord:
        """FileRecord를 생성합니다.
        
        Args:
            file_path: 파일 경로
            detect_encoding: 인코딩 감지 여부 (기본값: True)
        
        Returns:
            생성된 FileRecord 객체
        
        Raises:
            FileEncodingError: 인코딩 감지 실패 시
            OSError: 파일 메타데이터 읽기 실패 시
        """
        # 파일 크기 (O(1) - 메타데이터만 읽음)
        file_size = file_path.stat().st_size
        
        # 인코딩 감지 (정책 변경: 스캔 단계에서 encoding 확정)
        # 이후 단계에서 재감지하지 않도록 실제 인코딩 값을 저장
        encoding = ENCODING_NOT_DETECTED
        if detect_encoding:
            try:
                encoding = detect_encoding_path(file_path)
                # "Unknown", "Empty", "N/A"는 기본값으로 처리
                if encoding in (ENCODING_UNKNOWN, ENCODING_EMPTY, ENCODING_NA):
                    encoding = DEFAULT_ENCODING
            except FileEncodingError as e:
                self._logger.warning(f"인코딩 감지 실패: {file_path} - {e}")
                encoding = DEFAULT_ENCODING
        
        # 파일명 파싱 (제목, 정규화 제목, 회차 범위)
        title = extract_title(file_path.name)
        normalized_title = extract_normalized_title(file_path.name)
        episode_range = extract_episode_range(file_path.name)
        
        # 부분 해싱 기반 중복 탐지용 필드 추출
        base_title = extract_base_title(file_path.name)
        episode_end = extract_episode_end(file_path.name)
        variant_flags = extract_variant_flags(file_path.name)
        
        # 파일 수정 시간 (mtime)
        mtime = file_path.stat().st_mtime
        
        # FileRecord 생성
        file_record = FileRecord(
            path=file_path,
            name=file_path.name,
            size=file_size,
            encoding=encoding,
            title=title if title else None,
            normalized_title=normalized_title if normalized_title else None,
            episode_range=episode_range,
            base_title=base_title if base_title else None,
            episode_end=episode_end,
            variant_flags=variant_flags if variant_flags else None,
            mtime=mtime,
        )
        
        return file_record

