"""애플리케이션 상태 관리.

AppState와 ProgressState를 정의하여 GUI 상태를 관리.
"""

# 표준 라이브러리
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# 서드파티
from PySide6.QtCore import QObject, Signal


@dataclass
class AppState:
    """애플리케이션 상태.
    
    Attributes:
        is_scanning: 스캔 작업 실행 중 여부
        current_job: 현재 실행 중인 작업 이름
        scan_folder: 스캔 대상 폴더 경로
    """
    is_scanning: bool = False
    current_job: Optional[str] = None
    scan_folder: Optional[Path] = None


@dataclass
class ProgressState:
    """진행률 상태.
    
    Attributes:
        current_stage: 현재 단계 이름
        stage_progress: 현재 단계 진행률 (0-100)
        overall_progress: 전체 진행률 (0-100)
        files_processed: 처리 완료 파일 수
        files_total: 전체 파일 수
        speed: 처리 속도 (files/sec)
        eta_seconds: 예상 남은 시간 (초)
        current_file: 현재 처리 중인 파일 경로
    """
    current_stage: str = "대기 중"
    stage_progress: int = 0
    overall_progress: int = 0
    files_processed: int = 0
    files_total: int = 0
    speed: float = 0.0
    eta_seconds: int = 0
    current_file: Optional[str] = None


class StateManager(QObject):
    """상태 관리자.
    
    상태 변경 시그널을 제공하여 GUI 업데이트를 트리거.
    """
    
    # 상태 변경 시그널
    stateChanged = Signal(AppState)
    progressUpdated = Signal(ProgressState)
    
    def __init__(self, parent=None) -> None:
        """상태 관리자 초기화.
        
        Args:
            parent: 부모 객체
        """
        super().__init__(parent)
        self._app_state = AppState()
        self._progress_state = ProgressState()
    
    @property
    def app_state(self) -> AppState:
        """애플리케이션 상태 반환.
        
        Returns:
            AppState 인스턴스
        """
        return self._app_state
    
    @property
    def progress_state(self) -> ProgressState:
        """진행률 상태 반환.
        
        Returns:
            ProgressState 인스턴스
        """
        return self._progress_state
    
    def update_app_state(self, **kwargs) -> None:
        """애플리케이션 상태 업데이트.
        
        Args:
            **kwargs: 업데이트할 상태 필드
        """
        for key, value in kwargs.items():
            if hasattr(self._app_state, key):
                setattr(self._app_state, key, value)
        self.stateChanged.emit(self._app_state)
    
    def update_progress(self, **kwargs) -> None:
        """진행률 상태 업데이트.
        
        Args:
            **kwargs: 업데이트할 진행률 필드
        """
        for key, value in kwargs.items():
            if hasattr(self._progress_state, key):
                setattr(self._progress_state, key, value)
        self.progressUpdated.emit(self._progress_state)

