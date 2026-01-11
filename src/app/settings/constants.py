"""애플리케이션 상수 정의."""
from typing import Final

# 기본 텍스트 파일 확장자
DEFAULT_TEXT_EXTENSIONS: Final[list[str]] = [
    ".txt", ".md", ".log", ".rtf", ".doc", ".docx",
    ".html", ".htm", ".xml", ".json", ".csv",
    ".py", ".js", ".java", ".cpp", ".c", ".h",
    ".css", ".scss", ".sass", ".less",
    ".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf",
    ".sh", ".bat", ".cmd", ".ps1",
    ".sql", ".r", ".m", ".pl", ".rb", ".go", ".rs",
]

# QSettings 키
SETTINGS_KEY_SCAN_FOLDER: Final[str] = "scan/last_folder"
SETTINGS_KEY_EXTENSION_FILTER: Final[str] = "scan/extension_filter"
SETTINGS_KEY_INCLUDE_SUBDIRS: Final[str] = "scan/include_subdirs"
SETTINGS_KEY_INCLUDE_HIDDEN: Final[str] = "scan/include_hidden"
SETTINGS_KEY_INCLUDE_SYMLINKS: Final[str] = "scan/include_symlinks"
SETTINGS_KEY_INCREMENTAL_SCAN: Final[str] = "scan/incremental_scan"
