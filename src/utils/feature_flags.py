"""
Feature Flag 유틸리티

리팩토링 중 새 로직을 안전하게 토글할 수 있도록 하는 Feature Flag 지원입니다.
"""

import os
from typing import Optional


def get_feature_flag(flag_name: str, default: bool = False) -> bool:
    """Feature Flag 값을 가져옵니다.
    
    환경변수에서 Feature Flag를 읽습니다.
    환경변수가 설정되지 않았으면 기본값을 반환합니다.
    
    Args:
        flag_name: Feature Flag 이름 (예: "ENCODING_DETECTOR_V2")
        default: 기본값 (기본값: False)
        
    Returns:
        Feature Flag 값 (bool)
        
    Example:
        >>> # 환경변수 ENCODING_DETECTOR_V2=1 설정 시
        >>> get_feature_flag("ENCODING_DETECTOR_V2")
        True
        >>> # 환경변수 미설정 시
        >>> get_feature_flag("ENCODING_DETECTOR_V2", default=False)
        False
    """
    env_value = os.getenv(flag_name)
    if env_value is None:
        return default
    
    # "1", "true", "True", "TRUE" 등을 True로 처리
    env_value_lower = env_value.lower().strip()
    return env_value_lower in ("1", "true", "yes", "on", "enabled")


def is_encoding_detector_v2_enabled() -> bool:
    """ENCODING_DETECTOR_V2 Feature Flag가 활성화되었는지 확인합니다.
    
    Returns:
        ENCODING_DETECTOR_V2가 활성화되었으면 True
    """
    return get_feature_flag("ENCODING_DETECTOR_V2", default=False)

