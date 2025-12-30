"""
로깅 유틸리티 모듈

애플리케이션 전반에서 사용할 로거를 설정하고 제공합니다.
"""

import logging
import sys
from pathlib import Path
from typing import Optional


def setup_logger(
    name: str = "NovelGuard",
    log_file: Optional[Path] = None,
    level: int = logging.INFO
) -> logging.Logger:
    """로거를 설정하고 반환합니다.
    
    파일 및 콘솔 핸들러를 설정하여 로그를 기록합니다.
    파일 핸들러는 지정된 파일에 기록하고,
    콘솔 핸들러는 표준 출력에 기록합니다.
    
    Args:
        name: 로거 이름 (기본값: "NovelGuard")
        log_file: 로그 파일 경로 (None이면 파일 핸들러 미사용)
        level: 로그 레벨 (기본값: logging.INFO)
        
    Returns:
        설정된 로거 객체
        
    Example:
        >>> logger = setup_logger("MyModule")
        >>> logger.info("로그 메시지")
    """
    logger = logging.getLogger(name)
    
    # 이미 핸들러가 설정되어 있으면 기존 로거 반환
    if logger.handlers:
        return logger
    
    logger.setLevel(level)
    
    # 로그 포맷 설정
    # 형식: [YYYY-MM-DD HH:MM:SS] LEVEL - 메시지 (파일명:라인번호)
    formatter = logging.Formatter(
        fmt="[%(asctime)s] %(levelname)s - %(message)s (%(filename)s:%(lineno)d)",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # 콘솔 핸들러 (항상 추가)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 파일 핸들러 (선택적)
    if log_file:
        try:
            # 로그 디렉토리 생성
            log_file.parent.mkdir(parents=True, exist_ok=True)
            
            file_handler = logging.FileHandler(log_file, encoding="utf-8")
            file_handler.setLevel(level)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except (OSError, PermissionError) as e:
            # 파일 핸들러 생성 실패 시 경고만 출력하고 계속 진행
            logger.warning(f"로그 파일 핸들러 생성 실패: {e}")
    
    return logger


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """기존 로거를 가져오거나 새로 생성합니다.
    
    Args:
        name: 로거 이름 (None이면 루트 로거)
        
    Returns:
        로거 객체
    """
    if name:
        return logging.getLogger(f"NovelGuard.{name}")
    return logging.getLogger("NovelGuard")

