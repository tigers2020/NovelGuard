"""데이터베이스 경로 처리."""
import os
import sys
from pathlib import Path


def get_app_data_dir() -> Path:
    """플랫폼별 앱 데이터 디렉토리 반환.
    
    Returns:
        앱 데이터 디렉토리 Path.
    """
    if os.name == 'nt':  # Windows
        app_data = os.getenv('APPDATA')
        if app_data:
            return Path(app_data) / "NovelGuard"
        # Fallback (일반적이지 않지만)
        return Path.home() / "AppData" / "Roaming" / "NovelGuard"
    elif os.name == 'posix':  # macOS, Linux
        if sys.platform == 'darwin':  # macOS
            return Path.home() / "Library" / "Application Support" / "NovelGuard"
        else:  # Linux
            xdg_data_home = os.getenv('XDG_DATA_HOME')
            if xdg_data_home:
                return Path(xdg_data_home) / "NovelGuard"
            return Path.home() / ".local" / "share" / "NovelGuard"
    else:
        # Unknown platform, use home directory
        return Path.home() / ".novelguard"


def get_index_db_path() -> Path:
    """인덱스 DB 파일 경로 반환.
    
    디렉토리가 없으면 자동 생성합니다.
    
    Returns:
        인덱스 DB 파일 Path.
    """
    app_data_dir = get_app_data_dir()
    app_data_dir.mkdir(parents=True, exist_ok=True)
    return app_data_dir / "index.db"
