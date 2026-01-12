"""중복 탐지 요청 DTO."""
from dataclasses import dataclass


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
