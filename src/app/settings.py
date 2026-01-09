"""설정 관리.

QSettings/Config 관리.
"""

from pathlib import Path
from PySide6.QtCore import QSettings


class AppSettings:
    """애플리케이션 설정 관리."""
    
    def __init__(self) -> None:
        """AppSettings 초기화."""
        self.settings = QSettings("NovelGuard", "NovelGuard")
    
    def get_last_folder(self) -> str:
        """마지막 선택 폴더 반환.
        
        Returns:
            폴더 경로
        """
        return self.settings.value("last_folder", "", type=str)
    
    def set_last_folder(self, folder: str) -> None:
        """마지막 선택 폴더 저장.
        
        Args:
            folder: 폴더 경로
        """
        self.settings.setValue("last_folder", folder)
    
    def get_extensions(self) -> str:
        """확장자 필터 반환.
        
        Returns:
            확장자 필터 문자열
        """
        return self.settings.value("extensions", "", type=str)
    
    def set_extensions(self, extensions: str) -> None:
        """확장자 필터 저장.
        
        Args:
            extensions: 확장자 필터 문자열
        """
        self.settings.setValue("extensions", extensions)
    
    def get_scan_option(self, key: str, default: bool = True) -> bool:
        """스캔 옵션 반환.
        
        Args:
            key: 옵션 키
            default: 기본값
        
        Returns:
            옵션 값
        """
        return self.settings.value(f"scan_options/{key}", default, type=bool)
    
    def set_scan_option(self, key: str, value: bool) -> None:
        """스캔 옵션 저장.
        
        Args:
            key: 옵션 키
            value: 옵션 값
        """
        self.settings.setValue(f"scan_options/{key}", value)

