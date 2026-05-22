"""Application-wide constants (business policy, not Qt shell settings)."""

from typing import Final


class Constants:
    """애플리케이션 상수 클래스.

    모든 매직 넘버와 하드코딩된 값들을 중앙에서 관리합니다.
    모든 상수는 UPPER_SNAKE_CASE로 정의되며 Final 타입 힌팅을 사용합니다.
    """

    # ============================================================================
    # 바이트 변환 상수
    # ============================================================================

    BYTES_PER_KB: Final[int] = 1024
    BYTES_PER_MB: Final[int] = 1024 * 1024
    BYTES_PER_GB: Final[int] = 1024 * 1024 * 1024

    # ============================================================================
    # 파일 크기 임계값
    # ============================================================================

    MIN_FILE_SIZE: Final[int] = 1024
    MIN_ENCODING_DETECTION_SIZE: Final[int] = 100
    MAX_SAMPLE_SIZE: Final[int] = 32 * 1024
    LARGE_FILE_THRESHOLD: Final[int] = 5 * 1024 * 1024
    TEXT_FILE_MAX_SIZE: Final[int] = 10 * 1024 * 1024
    MIN_TEXT_FILE_SIZE: Final[int] = 100
    SAMPLE_SIZE: Final[int] = 65536
    SMALL_FILE_THRESHOLD: Final[int] = 1024

    # ============================================================================
    # 인코딩 관련 상수
    # ============================================================================

    DEFAULT_ENCODING: Final[str] = "utf-8"
    TARGET_ENCODING: Final[str] = "UTF-8"
    LOG_FILE_ENCODING: Final[str] = "utf-8"
    MIN_ENCODING_CONFIDENCE: Final[float] = 0.5
    INTEGRITY_ENCODING_MIN_CONFIDENCE: Final[float] = 0.7
    HIGH_ENCODING_CONFIDENCE: Final[float] = 0.9
    INTEGRITY_SAMPLE_BYTES: Final[int] = SAMPLE_SIZE
    UTF8_BACKUP_SUFFIX: Final[str] = ".novelguard.bak"

    # ============================================================================
    # 해시 관련 상수
    # ============================================================================

    HASH_ALGORITHM: Final[str] = "sha256"
    FINGERPRINT_ALGORITHM: Final[str] = "sha256"
    HEAD_HASH_SIZE: Final[int] = 1024

    # ============================================================================
    # 중복 탐지 관련 상수
    # ============================================================================

    MIN_DUPLICATE_CONFIDENCE: Final[float] = 0.5
    DEFAULT_SIMILARITY_THRESHOLD: Final[float] = 0.85
    CONFIDENCE_THRESHOLD: Final[float] = 0.5

    # ============================================================================
    # 점수 체계 상수 (KeeperScoreService)
    # ============================================================================

    SCORE_COMPLETE_TAG: Final[int] = 100
    SCORE_COVERAGE: Final[int] = 50
    SCORE_MTIME: Final[int] = 20
    SCORE_SIZE: Final[int] = 10
    PENALTY_LOW_CONFIDENCE: Final[int] = -1000

    # ============================================================================
    # UI/Display 관련 상수
    # ============================================================================

    DISPLAY_KB_THRESHOLD: Final[int] = 1024
    DISPLAY_MB_THRESHOLD: Final[int] = 1024 * 1024
    DISPLAY_GB_THRESHOLD: Final[int] = 1024 * 1024 * 1024
    DEFAULT_SIMILARITY_PERCENT: Final[int] = 85
    SIMILARITY_MIN_PERCENT: Final[int] = 50
    SIMILARITY_MAX_PERCENT: Final[int] = 100
    DEFAULT_CACHE_SIZE_MB: Final[int] = 512
    DEFAULT_WORKER_THREADS: Final[int] = 8
    DEFAULT_CONFLICT_POLICY_INDEX: Final[int] = 1
    PROGRESS_MAX_PERCENT: Final[int] = 100

    # ============================================================================
    # 시간 변환 상수
    # ============================================================================

    MILLISECONDS_PER_SECOND: Final[int] = 1000

    # ============================================================================
    # 로깅 관련 상수
    # ============================================================================

    MAX_LOG_ENTRIES: Final[int] = 10000

    # ============================================================================
    # 애플리케이션 메타데이터
    # ============================================================================

    APP_NAME: Final[str] = "NovelGuard"
    APP_ORGANIZATION: Final[str] = "NovelGuard"
    APP_VERSION: Final[str] = "0.1.0"


DEFAULT_TEXT_EXTENSIONS: Final[list[str]] = [
    ".txt",
    ".md",
    ".log",
    ".rtf",
    ".doc",
    ".docx",
    ".html",
    ".htm",
    ".xml",
    ".json",
    ".csv",
    ".py",
    ".js",
    ".java",
    ".cpp",
    ".c",
    ".h",
    ".css",
    ".scss",
    ".sass",
    ".less",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".cfg",
    ".conf",
    ".sh",
    ".bat",
    ".cmd",
    ".ps1",
    ".sql",
    ".r",
    ".m",
    ".pl",
    ".rb",
    ".go",
    ".rs",
]
