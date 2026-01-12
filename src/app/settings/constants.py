"""애플리케이션 상수 정의."""
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
    """1KB의 바이트 수 (1024)."""
    
    BYTES_PER_MB: Final[int] = 1024 * 1024
    """1MB의 바이트 수 (1,048,576)."""
    
    BYTES_PER_GB: Final[int] = 1024 * 1024 * 1024
    """1GB의 바이트 수 (1,073,741,824)."""
    
    # ============================================================================
    # 파일 크기 임계값
    # ============================================================================
    
    MIN_FILE_SIZE: Final[int] = 1024
    """최소 파일 크기 (1KB). 파일 크기 검증에 사용."""
    
    MIN_ENCODING_DETECTION_SIZE: Final[int] = 100
    """인코딩 감지 최소 파일 크기 (100 bytes)."""
    
    MAX_SAMPLE_SIZE: Final[int] = 32 * 1024
    """최대 샘플 크기 (32KB)."""
    
    LARGE_FILE_THRESHOLD: Final[int] = 5 * 1024 * 1024
    """대용량 파일 임계값 (5MB)."""
    
    TEXT_FILE_MAX_SIZE: Final[int] = 10 * 1024 * 1024
    """텍스트 파일 최대 크기 (10MB)."""
    
    MIN_TEXT_FILE_SIZE: Final[int] = 100
    """최소 텍스트 파일 크기 (100 bytes). 무결성 검사에 사용."""
    
    SAMPLE_SIZE: Final[int] = 65536
    """해시 계산 샘플 크기 (64KB). prefix/suffix hash 계산에 사용."""
    
    SMALL_FILE_THRESHOLD: Final[int] = 1024
    """작은 파일 임계값 (1KB). 통계 및 필터링에 사용."""
    
    # ============================================================================
    # 인코딩 관련 상수
    # ============================================================================
    
    DEFAULT_ENCODING: Final[str] = "utf-8"
    """기본 인코딩 (UTF-8)."""
    
    TARGET_ENCODING: Final[str] = "UTF-8"
    """대상 인코딩 (UTF-8)."""
    
    LOG_FILE_ENCODING: Final[str] = "utf-8"
    """로그 파일 인코딩 (UTF-8)."""
    
    MIN_ENCODING_CONFIDENCE: Final[float] = 0.5
    """인코딩 감지 최소 신뢰도 (0.5)."""
    
    HIGH_ENCODING_CONFIDENCE: Final[float] = 0.9
    """인코딩 감지 높은 신뢰도 (0.9)."""
    
    # ============================================================================
    # 해시 관련 상수
    # ============================================================================
    
    HASH_ALGORITHM: Final[str] = "sha256"
    """해시 알고리즘 (SHA256)."""
    
    FINGERPRINT_ALGORITHM: Final[str] = "sha256"
    """핑거프린트 알고리즘 (SHA256)."""
    
    HEAD_HASH_SIZE: Final[int] = 1024
    """헤더 해시 크기 (1KB)."""
    
    # ============================================================================
    # 중복 탐지 관련 상수
    # ============================================================================
    
    MIN_DUPLICATE_CONFIDENCE: Final[float] = 0.5
    """중복 탐지 최소 신뢰도 (0.5)."""
    
    DEFAULT_SIMILARITY_THRESHOLD: Final[float] = 0.85
    """기본 유사도 임계값 (0.85). Near 중복 탐지에 사용."""
    
    CONFIDENCE_THRESHOLD: Final[float] = 0.5
    """신뢰도 임계값 (0.5). 파싱 신뢰도 검증에 사용."""
    
    # ============================================================================
    # 점수 체계 상수 (KeeperScoreService)
    # ============================================================================
    
    SCORE_COMPLETE_TAG: Final[int] = 100
    """완결 태그 점수 (100). Keeper 점수 계산에 사용."""
    
    SCORE_COVERAGE: Final[int] = 50
    """커버리지 점수 계수 (50). Keeper 점수 계산에 사용."""
    
    SCORE_MTIME: Final[int] = 20
    """수정 시간 최신 점수 (20). Keeper 점수 계산에 사용."""
    
    SCORE_SIZE: Final[int] = 10
    """파일 크기 큰 점수 (10). Keeper 점수 계산에 사용."""
    
    PENALTY_LOW_CONFIDENCE: Final[int] = -1000
    """파싱 신뢰도 낮음 페널티 (-1000). Keeper 점수 계산에 사용."""
    
    # ============================================================================
    # UI/Display 관련 상수
    # ============================================================================
    
    DISPLAY_KB_THRESHOLD: Final[int] = 1024
    """KB 표시 임계값 (1KB). 파일 크기 표시에 사용."""
    
    DISPLAY_MB_THRESHOLD: Final[int] = 1024 * 1024
    """MB 표시 임계값 (1MB). 파일 크기 표시에 사용."""
    
    DISPLAY_GB_THRESHOLD: Final[int] = 1024 * 1024 * 1024
    """GB 표시 임계값 (1GB). 파일 크기 표시에 사용."""
    
    DEFAULT_SIMILARITY_PERCENT: Final[int] = 85
    """기본 유사도 퍼센트 (85%). UI 슬라이더 기본값."""
    
    SIMILARITY_MIN_PERCENT: Final[int] = 50
    """유사도 최소 퍼센트 (50%). UI 슬라이더 최소값."""
    
    SIMILARITY_MAX_PERCENT: Final[int] = 100
    """유사도 최대 퍼센트 (100%). UI 슬라이더 최대값."""
    
    DEFAULT_CACHE_SIZE_MB: Final[int] = 512
    """기본 캐시 크기 (512MB). 성능 설정 기본값."""
    
    DEFAULT_WORKER_THREADS: Final[int] = 8
    """기본 워커 스레드 수 (8). 성능 설정 기본값."""
    
    DEFAULT_CONFLICT_POLICY_INDEX: Final[int] = 1
    """기본 충돌 정책 인덱스 (1 = 접미사 추가)."""
    
    PROGRESS_MAX_PERCENT: Final[int] = 100
    """프로그레스 바 최대값 (100%)."""
    
    # ============================================================================
    # 시간 변환 상수
    # ============================================================================
    
    MILLISECONDS_PER_SECOND: Final[int] = 1000
    """초당 밀리초 수 (1000). 시간 변환에 사용."""
    
    # ============================================================================
    # 로깅 관련 상수
    # ============================================================================
    
    MAX_LOG_ENTRIES: Final[int] = 10000
    """최대 로그 엔트리 수 (10000). InMemoryLogSink에 사용."""
    
    # ============================================================================
    # 애플리케이션 메타데이터
    # ============================================================================
    
    APP_NAME: Final[str] = "NovelGuard"
    """애플리케이션 이름."""
    
    APP_ORGANIZATION: Final[str] = "NovelGuard"
    """애플리케이션 조직명."""
    
    APP_VERSION: Final[str] = "0.1.0"
    """애플리케이션 버전."""


# ============================================================================
# 기존 모듈 레벨 상수 (하위 호환성 유지)
# ============================================================================

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

# 중복 탐지 설정 키
SETTINGS_KEY_EXACT_DUPLICATE: Final[str] = "duplicate/exact_duplicate"
SETTINGS_KEY_NEAR_DUPLICATE: Final[str] = "duplicate/near_duplicate"
SETTINGS_KEY_INCLUDE_RELATION: Final[str] = "duplicate/include_relation"
SETTINGS_KEY_SIMILARITY_PERCENT: Final[str] = "duplicate/similarity_percent"
SETTINGS_KEY_CONFLICT_POLICY: Final[str] = "duplicate/conflict_policy"

# 성능 설정 키
SETTINGS_KEY_WORKER_THREADS: Final[str] = "performance/worker_threads"
SETTINGS_KEY_CACHE_SIZE_MB: Final[str] = "performance/cache_size_mb"
