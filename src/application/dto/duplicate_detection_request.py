"""중복 탐지 요청 DTO."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class DuplicateDetectionRequest:
    """중복 탐지 요청 DTO."""

    run_id: int
    """스캔 run_id."""

    enable_exact: bool = True
    """Exact 중복 탐지 활성화."""

    enable_version: bool = True
    """Version 중복 탐지 활성화."""

    enable_containment: bool = True
    """Containment 관계 탐지 활성화."""

    enable_near: bool = False
    """Near 중복 탐지 활성화 (기본값: False, 비용 큼)."""

    near_similarity_threshold: float = 0.85
    """Near 중복 유사도 임계값 (0.0 ~ 1.0)."""

    blocking_confidence_min: float = 0.7
    """Blocking에 포함할 파싱 결과의 최소 confidence (0.0 ~ 1.0). 이보다 낮으면 후보에서 제외."""

    min_confidence: Optional[float] = None
    """결과 그룹 최소 신뢰도. None이면 필터 없음. 설정 시 이 값 미만인 그룹은 제외."""
