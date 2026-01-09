"""파일 스캔 유스케이스."""

from pathlib import Path
from typing import Callable, Optional
from infra.fs.file_scanner import FileScanner
from infra.hashing.hash_calculator import HashCalculator
from infra.hashing.fingerprint import FingerprintGenerator
from infra.encoding.encoding_detector import EncodingDetector
from infra.db.file_repository import FileRepository
from domain.models.file_record import FileRecord
from common.logging import setup_logging

logger = setup_logging()


class ScanFilesUseCase:
    """파일 스캔 유스케이스."""
    
    def __init__(
        self,
        repository: FileRepository,
        scanner: Optional[FileScanner] = None,
        hash_calculator: Optional[HashCalculator] = None,
        fingerprint_generator: Optional[FingerprintGenerator] = None,
        encoding_detector: Optional[EncodingDetector] = None
    ) -> None:
        """유스케이스 초기화.
        
        Args:
            repository: FileRepository
            scanner: FileScanner (None이면 기본값)
            hash_calculator: HashCalculator (None이면 기본값)
            fingerprint_generator: FingerprintGenerator (None이면 기본값)
            encoding_detector: EncodingDetector (None이면 기본값)
        """
        self.repository = repository
        self.scanner = scanner or FileScanner()
        self.hash_calculator = hash_calculator or HashCalculator()
        self.fingerprint_generator = fingerprint_generator or FingerprintGenerator()
        self.encoding_detector = encoding_detector or EncodingDetector()
    
    def execute(
        self,
        root_path: Path,
        progress_callback: Optional[Callable[[int, int, Path], None]] = None
    ) -> list[FileRecord]:
        """파일 스캔 실행.
        
        Args:
            root_path: 루트 경로
            progress_callback: 진행 상황 콜백 (current, total, current_path)
        
        Returns:
            FileRecord 리스트
        """
        records = []
        file_paths = list(self.scanner.scan_directory(root_path))
        total = len(file_paths)
        
        for idx, file_path in enumerate(file_paths):
            try:
                record = self._scan_file(file_path)
                saved_record = self.repository.save(record)
                records.append(saved_record)
                
                if progress_callback:
                    progress_callback(idx + 1, total, file_path)
            except Exception as e:
                logger.error(f"파일 스캔 실패: {file_path} - {e}")
        
        return records
    
    def _scan_file(self, file_path: Path) -> FileRecord:
        """단일 파일 스캔.
        
        Args:
            file_path: 파일 경로
        
        Returns:
            FileRecord
        """
        stat = file_path.stat()
        
        # 기본 메타데이터
        record = FileRecord(
            file_id=0,  # repository에서 할당
            path=file_path,
            name=file_path.name,
            ext=file_path.suffix,
            size=stat.st_size,
            mtime=stat.st_mtime,
            is_text=False,  # 나중에 업데이트
        )
        
        # 텍스트 파일 여부 및 인코딩 감지
        try:
            encoding, confidence = self.encoding_detector.detect(file_path)
            record.encoding_detected = encoding
            record.encoding_confidence = confidence
            record.is_text = encoding is not None
        except Exception as e:
            logger.warning(f"인코딩 감지 실패: {file_path} - {e}")
        
        # 빠른 지문 생성
        try:
            record.fingerprint_fast = self.fingerprint_generator.generate_fast_fingerprint(file_path)
        except Exception as e:
            logger.warning(f"빠른 지문 생성 실패: {file_path} - {e}")
        
        # 작은 파일이면 해시 계산 건너뛰기
        if stat.st_size > 1024 * 1024:  # 1MB 이상
            # MD5 해시 계산 (빠름)
            try:
                record.hash_strong = self.hash_calculator.calculate_md5(file_path)
            except Exception as e:
                logger.warning(f"해시 계산 실패: {file_path} - {e}")
        
        return record

