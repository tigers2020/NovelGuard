"""스냅샷 정규화 헬퍼 모듈.

비결정적 요소를 제거하여 OS/환경 독립적인 스냅샷 비교를 가능하게 합니다.
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime


def normalize_snapshot(data: Any, base_path: Optional[Path] = None) -> Any:
    """스냅샷 정규화 (비결정적 요소 제거).
    
    Args:
        data: 정규화할 데이터 (dict, list, primitive 등)
        base_path: 기준 경로 (절대 경로를 상대 경로로 변환할 때 사용)
    
    Returns:
        정규화된 데이터
    """
    if isinstance(data, dict):
        return _normalize_dict(data, base_path)
    elif isinstance(data, list):
        return _normalize_list(data, base_path)
    elif isinstance(data, (set, frozenset)):
        return _normalize_list(sorted(data, key=_sort_key), base_path)
    elif isinstance(data, (int, bool, type(None))):
        return data
    elif isinstance(data, float):
        return round(data, 6)  # 소수점 6자리로 반올림
    elif isinstance(data, str):
        return _normalize_string(data, base_path)
    else:
        # 기타 타입은 문자열로 변환
        return str(data)


def _normalize_dict(data: Dict[str, Any], base_path: Optional[Path] = None) -> Dict[str, Any]:
    """딕셔너리 정규화."""
    # 비결정 필드 제거 (정확한 필드명만 매칭)
    non_deterministic_fields = {
        'mtime', 'created_at', 'updated_at', 'timestamp', 'duration',
        'memory_usage', 'cpu_time', 'process_id', 'thread_id', 'pid', 'tid',
        'random_id', 'session_id', 'request_id'
    }
    
    # 유지해야 하는 ID 필드들
    preserved_id_fields = {
        'file_id', 'group_id', 'issue_id', 'action_id', 'canonical_id', 
        'member_ids', 'id'  # 일반적인 'id'도 유지
    }
    
    result = {}
    for key, value in sorted(data.items(), key=lambda x: _sort_key(x[0])):
        key_lower = key.lower()
        
        # 비결정 필드 체크 (정확한 매칭만)
        if key_lower in non_deterministic_fields:
            continue
        
        # 타임스탬프 관련 필드 체크 (정확한 필드명만)
        if key_lower in ['mtime', 'created_at', 'updated_at', 'timestamp', 'duration']:
            continue
        
        # UUID 필드 체크
        if 'uuid' in key_lower and key not in preserved_id_fields:
            continue
        
        normalized_value = normalize_snapshot(value, base_path)
        result[key] = normalized_value
    
    return result


def _normalize_list(data: List[Any], base_path: Optional[Path] = None) -> List[Any]:
    """리스트 정규화 (stable sort)."""
    if not data:
        return []
    
    # 첫 번째 원소로 타입 판단
    first_elem = data[0]
    
    if isinstance(first_elem, dict):
        # 딕셔너리 리스트: file_id, group_id, id 등으로 정렬
        sort_key_fn = lambda x: (
            x.get('file_id', 0) if isinstance(x, dict) else 0,
            x.get('group_id', 0) if isinstance(x, dict) else 0,
            x.get('issue_id', 0) if isinstance(x, dict) else 0,
            x.get('id', 0) if isinstance(x, dict) else 0,  # 일반 'id' 필드도 정렬 키로 사용
            str(x.get('path', '')) if isinstance(x, dict) else str(x),
        )
        sorted_data = sorted(data, key=sort_key_fn)
    elif isinstance(first_elem, (int, float, str)):
        # 원시 타입 리스트: 직접 정렬
        sorted_data = sorted(data, key=_sort_key)
    else:
        # 기타 타입: 문자열로 변환하여 정렬
        sorted_data = sorted(data, key=lambda x: str(x))
    
    return [normalize_snapshot(item, base_path) for item in sorted_data]


def _normalize_string(value: str, base_path: Optional[Path] = None) -> str:
    """문자열 정규화 (경로 처리)."""
    # 경로 정규화: 절대 경로를 상대 경로로 변환
    if base_path and os.path.isabs(value):
        try:
            # Path 객체를 문자열로 변환
            base_path_str = str(base_path)
            # 상대 경로로 변환 시도
            rel_path = os.path.relpath(value, base_path_str)
            # OS 경로 구분자 통일 (백슬래시 → 슬래시)
            normalized = rel_path.replace('\\', '/')
            # 상대 경로 변환이 성공했는지 확인 (상대 경로는 '..'로 시작하지 않거나 같은 경로 내)
            if not os.path.isabs(normalized):
                return normalized
        except (ValueError, OSError):
            # 변환 실패 시 원본 경로 사용 (OS 구분자만 통일)
            pass
    
    # OS 경로 구분자 통일
    return value.replace('\\', '/')


def _sort_key(value: Any) -> Any:
    """정렬 키 생성."""
    if isinstance(value, (int, float)):
        return (0, value)
    elif isinstance(value, str):
        return (1, value.lower())
    elif isinstance(value, bool):
        return (2, value)
    elif value is None:
        return (3, None)
    else:
        return (4, str(value))


def remove_timestamps(data: Dict[str, Any]) -> Dict[str, Any]:
    """타임스탬프 제거 (추가 유틸리티)."""
    result = {}
    timestamp_fields = {'mtime', 'created_at', 'updated_at', 'timestamp', 'date'}
    
    for key, value in data.items():
        if key.lower() in timestamp_fields:
            continue
        elif isinstance(value, dict):
            result[key] = remove_timestamps(value)
        elif isinstance(value, list):
            result[key] = [
                remove_timestamps(item) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            result[key] = value
    
    return result
