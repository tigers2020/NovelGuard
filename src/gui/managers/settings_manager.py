"""
설정 관리 모듈

애플리케이션 설정을 저장하고 로드하는 기능을 제공합니다.
"""

from pathlib import Path
from typing import Optional

from PySide6.QtCore import QSettings
from utils.logger import get_logger


class SettingsManager:
    """설정 관리 클래스.
    
    애플리케이션 설정을 저장하고 로드하는 기능을 제공합니다.
    QSettings를 사용하여 플랫폼별 설정 저장소에 저장합니다.
    
    Attributes:
        _logger: 로거 인스턴스
        _settings: QSettings 인스턴스
    """
    
    # 설정 키 상수
    SETTING_LAST_FOLDER = "last_selected_folder"
    
    def __init__(self) -> None:
        """SettingsManager 초기화."""
        self._logger = get_logger("SettingsManager")
        self._settings = QSettings("NovelGuard", "NovelGuard")
    
    def load_last_folder(self) -> str:
        """저장된 마지막 폴더 경로를 로드합니다.
        
        Returns:
            저장된 폴더 경로 문자열. 경로가 없거나 유효하지 않으면 빈 문자열.
        """
        try:
            last_folder = self._settings.value(self.SETTING_LAST_FOLDER, "")
            if not last_folder:
                return ""
            
            # 경로 유효성 검사
            folder_path = Path(last_folder)
            if folder_path.exists() and folder_path.is_dir():
                return str(folder_path)
            else:
                # 유효하지 않은 경로는 설정에서 제거
                self._settings.remove(self.SETTING_LAST_FOLDER)
                return ""
        except Exception:
            # 설정 읽기 오류 시 빈 문자열 반환
            return ""
    
    def save_last_folder(self, folder_path: str) -> None:
        """마지막 선택 폴더 경로를 저장합니다.
        
        Args:
            folder_path: 저장할 폴더 경로 문자열
        """
        try:
            self._settings.setValue(self.SETTING_LAST_FOLDER, folder_path)
            self._settings.sync()  # 설정 즉시 저장
            self._logger.debug(f"마지막 폴더 경로 저장: {folder_path}")
        except Exception as e:
            # 설정 저장 오류는 로그만 기록하고 무시 (기능 동작에는 영향 없음)
            self._logger.warning(f"마지막 폴더 경로 저장 실패: {e}")

