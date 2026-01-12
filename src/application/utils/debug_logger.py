"""디버깅 로그 유틸리티."""
import json
from contextlib import contextmanager
from functools import wraps
from time import time
from typing import Any, Callable, Optional

from application.dto.log_entry import LogEntry
from application.ports.log_sink import ILogSink
from datetime import datetime


def debug_log(
    log_sink: Optional[ILogSink],
    level: str = "DEBUG",
    include_params: bool = True,
    include_result: bool = True,
    max_param_length: int = 200
):
    """함수 실행 디버깅 로그 데코레이터.
    
    Args:
        log_sink: 로그 싱크 (None이면 로깅하지 않음).
        level: 로그 레벨 (기본값: "DEBUG").
        include_params: 파라미터 포함 여부 (기본값: True).
        include_result: 결과 포함 여부 (기본값: True).
        max_param_length: 파라미터/결과 최대 길이 (기본값: 200).
    
    Returns:
        데코레이터 함수.
    
    Example:
        ```python
        @debug_log(log_sink, level="DEBUG")
        def my_function(arg1, arg2):
            return result
        ```
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not log_sink:
                return func(*args, **kwargs)
            
            func_name = f"{func.__module__}.{func.__qualname__}"
            
            # ENTRY 로그
            params_summary = _summarize_params(args, kwargs, max_param_length) if include_params else "..."
            log_sink.write(LogEntry(
                timestamp=datetime.now(),
                level=level,
                message=f"{func_name} | ENTRY",
                context={"params": params_summary}
            ))
            
            # 실행 시간 측정
            start_time = time()
            try:
                result = func(*args, **kwargs)
                duration_ms = int((time() - start_time) * 1000)
                
                # EXIT 로그
                result_summary = _summarize_result(result, max_param_length) if include_result else "..."
                log_sink.write(LogEntry(
                    timestamp=datetime.now(),
                    level=level,
                    message=f"{func_name} | EXIT | {duration_ms}ms",
                    context={"result": result_summary}
                ))
                
                return result
            except Exception as e:
                duration_ms = int((time() - start_time) * 1000)
                log_sink.write(LogEntry(
                    timestamp=datetime.now(),
                    level="ERROR",
                    message=f"{func_name} | EXCEPTION | {duration_ms}ms",
                    context={"error": str(e), "error_type": type(e).__name__}
                ))
                raise
        
        return wrapper
    return decorator


def debug_step(
    log_sink: Optional[ILogSink],
    step_name: str,
    details: Optional[dict[str, Any]] = None
) -> None:
    """단계별 디버깅 로그.
    
    Args:
        log_sink: 로그 싱크 (None이면 로깅하지 않음).
        step_name: 단계 이름.
        details: 추가 상세 정보 (선택적).
    
    Example:
        ```python
        debug_step(log_sink, "directory_scan_start", {"path": "/path/to/dir"})
        ```
    """
    if log_sink:
        log_sink.write(LogEntry(
            timestamp=datetime.now(),
            level="DEBUG",
            message=f"STEP | {step_name}",
            context=details or {}
        ))


@contextmanager
def debug_context(
    log_sink: Optional[ILogSink],
    operation_name: str,
    details: Optional[dict[str, Any]] = None
):
    """디버깅 컨텍스트 매니저.
    
    Args:
        log_sink: 로그 싱크 (None이면 로깅하지 않음).
        operation_name: 작업 이름.
        details: 추가 상세 정보 (선택적).
    
    Example:
        ```python
        with debug_context(log_sink, "file_processing", {"file_path": "/path/to/file"}):
            # 작업 수행
            pass
        ```
    """
    if log_sink:
        start_time = time()
        log_sink.write(LogEntry(
            timestamp=datetime.now(),
            level="DEBUG",
            message=f"CONTEXT_START | {operation_name}",
            context=details or {}
        ))
    
    try:
        yield
    finally:
        if log_sink:
            duration_ms = int((time() - start_time) * 1000)
            log_sink.write(LogEntry(
                timestamp=datetime.now(),
                level="DEBUG",
                message=f"CONTEXT_END | {operation_name} | {duration_ms}ms",
                context={}
            ))


def _summarize_params(args: tuple, kwargs: dict, max_length: int) -> str:
    """파라미터 요약 생성.
    
    Args:
        args: 위치 인자 튜플.
        kwargs: 키워드 인자 딕셔너리.
        max_length: 최대 길이.
    
    Returns:
        파라미터 요약 문자열.
    """
    parts = []
    
    # 위치 인자 요약
    if args:
        args_str = _summarize_value(args, max_length // 2)
        parts.append(f"args={args_str}")
    
    # 키워드 인자 요약
    if kwargs:
        kwargs_str = _summarize_value(kwargs, max_length // 2)
        parts.append(f"kwargs={kwargs_str}")
    
    result = ", ".join(parts) if parts else "()"
    
    # 길이 제한
    if len(result) > max_length:
        result = result[:max_length - 3] + "..."
    
    return result


def _summarize_result(result: Any, max_length: int) -> str:
    """결과 요약 생성.
    
    Args:
        result: 결과 값.
        max_length: 최대 길이.
    
    Returns:
        결과 요약 문자열.
    """
    result_str = _summarize_value(result, max_length)
    
    # 길이 제한
    if len(result_str) > max_length:
        result_str = result_str[:max_length - 3] + "..."
    
    return result_str


def _summarize_value(value: Any, max_length: int) -> str:
    """값 요약 생성.
    
    Args:
        value: 요약할 값.
        max_length: 최대 길이.
    
    Returns:
        요약 문자열.
    """
    if value is None:
        return "None"
    
    # 기본 타입
    if isinstance(value, (str, int, float, bool)):
        return str(value)
    
    # 리스트/튜플
    if isinstance(value, (list, tuple)):
        if len(value) == 0:
            return "[]" if isinstance(value, list) else "()"
        
        # 첫 번째 요소만 표시
        first = _summarize_value(value[0], max_length // 2)
        count = len(value)
        result = f"[{first}, ...]" if isinstance(value, list) else f"({first}, ...)"
        if count > 1:
            result += f" (len={count})"
        return result
    
    # 딕셔너리
    if isinstance(value, dict):
        if len(value) == 0:
            return "{}"
        
        # 첫 번째 키-값만 표시
        first_key = list(value.keys())[0]
        first_val = _summarize_value(value[first_key], max_length // 3)
        count = len(value)
        result = f"{{'{first_key}': {first_val}, ...}}"
        if count > 1:
            result += f" (len={count})"
        return result
    
    # 객체 (Path, FileEntry 등)
    if hasattr(value, '__class__'):
        class_name = value.__class__.__name__
        
        # 특수 속성 확인
        if hasattr(value, 'path'):
            # Path 또는 FileEntry
            path_str = str(value.path) if hasattr(value.path, '__str__') else str(value.path)
            # 경로는 마지막 부분만 표시
            if len(path_str) > 30:
                path_str = "..." + path_str[-27:]
            return f"{class_name}(path='{path_str}')"
        
        if hasattr(value, '__dict__'):
            # 딕셔너리 속성
            attrs = {k: v for k, v in value.__dict__.items() if not k.startswith('_')}
            if attrs:
                first_key = list(attrs.keys())[0]
                first_val = _summarize_value(attrs[first_key], max_length // 3)
                return f"{class_name}({first_key}={first_val}, ...)"
        
        return f"{class_name}()"
    
    # 기타
    try:
        json_str = json.dumps(value, default=str, ensure_ascii=False)
        if len(json_str) > max_length:
            return json_str[:max_length - 3] + "..."
        return json_str
    except (TypeError, ValueError):
        return str(value)[:max_length]
