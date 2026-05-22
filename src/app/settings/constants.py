"""App shell settings: QSettings keys and backward-compatible re-exports."""

from typing import Final

from application.constants import DEFAULT_TEXT_EXTENSIONS, Constants  # noqa: F401

# QSettings 키 (PySide6 persistence only — stay in app/)
SETTINGS_KEY_UI_THEME: Final[str] = "ui/theme"

SETTINGS_KEY_SCAN_FOLDER: Final[str] = "scan/last_folder"
SETTINGS_KEY_EXTENSION_FILTER: Final[str] = "scan/extension_filter"
SETTINGS_KEY_INCLUDE_SUBDIRS: Final[str] = "scan/include_subdirs"
SETTINGS_KEY_INCLUDE_HIDDEN: Final[str] = "scan/include_hidden"
SETTINGS_KEY_INCLUDE_SYMLINKS: Final[str] = "scan/include_symlinks"
SETTINGS_KEY_INCREMENTAL_SCAN: Final[str] = "scan/incremental_scan"

SETTINGS_KEY_EXACT_DUPLICATE: Final[str] = "duplicate/exact_duplicate"
SETTINGS_KEY_NEAR_DUPLICATE: Final[str] = "duplicate/near_duplicate"
SETTINGS_KEY_INCLUDE_RELATION: Final[str] = "duplicate/include_relation"
SETTINGS_KEY_SIMILARITY_PERCENT: Final[str] = "duplicate/similarity_percent"
SETTINGS_KEY_CONFLICT_POLICY: Final[str] = "duplicate/conflict_policy"

SETTINGS_KEY_WORKER_THREADS: Final[str] = "performance/worker_threads"
SETTINGS_KEY_CACHE_SIZE_MB: Final[str] = "performance/cache_size_mb"
