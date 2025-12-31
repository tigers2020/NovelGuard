"""
파일 이동 모듈

파일을 안전하게 이동하는 기능을 제공합니다.
"""

from pathlib import Path
import shutil
import logging

from utils.logger import get_logger


class FileMover:
    """파일 이동 클래스.
    
    파일을 안전하게 이동하는 기능을 제공합니다.
    
    Attributes:
        _logger: 로거 인스턴스
    """
    
    def __init__(self) -> None:
        """FileMover 초기화."""
        self._logger = get_logger("FileMover")
    
    def move(self, source: Path, destination: Path, dry_run: bool = False) -> bool:
        """파일을 이동합니다.
        
        Args:
            source: 이동할 원본 파일 경로
            destination: 이동할 대상 경로
            dry_run: True이면 실제 이동 없이 시뮬레이션만 수행
        
        Returns:
            이동 성공 여부 (dry_run이면 항상 True)
        
        Raises:
            FileNotFoundError: 원본 파일이 없을 때
            OSError: 파일 이동 실패 시
        """
        if not source.exists():
            error_msg = f"원본 파일이 없습니다: {source}"
            self._logger.error(error_msg)
            raise FileNotFoundError(error_msg)
        
        if dry_run:
            self._logger.debug(f"[DRY-RUN] 파일 이동 시뮬레이션: {source} -> {destination}")
            return True
        
        try:
            # 부모 디렉토리 생성 (필요한 경우)
            destination.parent.mkdir(parents=True, exist_ok=True)
            
            # 파일 이동
            shutil.move(str(source), str(destination))
            self._logger.info(f"파일 이동 완료: {source} -> {destination}")
            return True
            
        except OSError as e:
            error_msg = f"파일 이동 실패: {source} -> {destination}, 오류: {e}"
            self._logger.error(error_msg, exc_info=True)
            raise

