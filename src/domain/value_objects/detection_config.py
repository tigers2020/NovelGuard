"""도메인 탐지 설정 상수."""

from typing import Final


class DetectionDefaults:
    """도메인 서비스가 사용하는 탐지·점수 기본값.

    app 레이어 의존 없이 도메인 레이어 안에서 완결되도록,
    탐지 관련 상수를 여기에 둔다.
    """

    SAMPLE_SIZE: Final[int] = 65536
    """해시 계산 샘플 크기 (64 KB). prefix/suffix hash에 사용."""

    DEFAULT_SIMILARITY_THRESHOLD: Final[float] = 0.85
    """Near 중복 탐지 기본 유사도 임계값."""

    CONFIDENCE_THRESHOLD: Final[float] = 0.5
    """파싱 신뢰도 최소 기준."""

    # Keeper 점수 체계
    SCORE_COMPLETE_TAG: Final[int] = 100
    SCORE_COVERAGE: Final[int] = 50
    SCORE_MTIME: Final[int] = 20
    SCORE_SIZE: Final[int] = 10
    PENALTY_LOW_CONFIDENCE: Final[int] = -1000
