"""스캔 결과 JSON 직렬화 유틸리티."""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from application.dto.scan_result import ScanResult
from domain.entities.file_entry import FileEntry

logger = logging.getLogger(__name__)


def serialize_scan_result_to_json(
    result: ScanResult,
    folder_path: Optional[Path] = None
) -> Dict[str, Any]:
    """ScanResult를 JSON 직렬화 가능한 딕셔너리로 변환.
    
    Args:
        result: 스캔 결과 DTO.
        folder_path: 스캔 폴더 경로 (선택적).
    
    Returns:
        JSON 직렬화 가능한 딕셔너리.
    """
    # 파일 엔트리 리스트 직렬화
    files: List[Dict[str, Any]] = []
    for entry in result.entries:
        file_dict: Dict[str, Any] = {
            "path": str(entry.path),
            "size": entry.size,
            "mtime": entry.mtime.isoformat() if isinstance(entry.mtime, datetime) else str(entry.mtime),
            "extension": entry.extension,
            "is_symlink": entry.is_symlink,
            "is_hidden": entry.is_hidden,
        }
        files.append(file_dict)
    
    # 스캔 정보 구성
    scan_info: Dict[str, Any] = {
        "scan_timestamp": result.scan_timestamp.isoformat() if result.scan_timestamp else None,
        "folder_path": str(folder_path) if folder_path else None,
        "total_files": result.total_files,
        "total_bytes": result.total_bytes,
        "elapsed_ms": result.elapsed_ms,
        "warnings_count": result.warnings_count,
    }
    
    return {
        "scan_info": scan_info,
        "files": files,
    }


def save_scan_result_to_json(
    result: ScanResult,
    output_path: Path,
    folder_path: Optional[Path] = None
) -> None:
    """ScanResult를 JSON 파일로 저장.
    
    Args:
        result: 스캔 결과 DTO.
        output_path: 저장할 JSON 파일 경로.
        folder_path: 스캔 폴더 경로 (선택적).
    
    Raises:
        OSError: 파일 쓰기 실패 시.
        ValueError: 직렬화 실패 시.
    """
    try:
        # 출력 디렉토리가 없으면 생성
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 딕셔너리로 변환
        data = serialize_scan_result_to_json(result, folder_path)
        
        # JSON 파일로 저장
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, sort_keys=True)
        
        logger.info(f"스캔 결과를 JSON 파일로 저장했습니다: {output_path}")
    
    except OSError as e:
        error_msg = f"스캔 결과 JSON 파일 저장 실패 (파일 시스템 오류): {output_path} - {e}"
        logger.error(error_msg)
        raise OSError(error_msg) from e
    
    except (ValueError, TypeError) as e:
        error_msg = f"스캔 결과 JSON 직렬화 실패: {e}"
        logger.error(error_msg)
        raise ValueError(error_msg) from e
    
    except Exception as e:
        error_msg = f"스캔 결과 JSON 저장 중 예상치 못한 오류: {output_path} - {e}"
        logger.error(error_msg, exc_info=True)
        raise


def generate_scan_json_filename(scan_timestamp: Optional[datetime] = None) -> str:
    """스캔 결과 JSON 파일명 생성.
    
    Args:
        scan_timestamp: 스캔 타임스탬프. None이면 현재 시간 사용.
    
    Returns:
        파일명 (예: "scan_results_20260108_234959.json").
    """
    if scan_timestamp is None:
        scan_timestamp = datetime.now()
    
    # 형식: scan_results_YYYYMMDD_HHMMSS.json
    timestamp_str = scan_timestamp.strftime("%Y%m%d_%H%M%S")
    return f"scan_results_{timestamp_str}.json"
