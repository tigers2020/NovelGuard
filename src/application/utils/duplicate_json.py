"""중복 탐지 결과 JSON 직렬화 유틸리티."""

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from application.constants import Constants
from application.dto.duplicate_group_result import DuplicateGroupResult

logger = logging.getLogger(__name__)


def serialize_duplicate_result_to_json(
    results: List[DuplicateGroupResult], file_data_store=None, folder_path: Optional[Path] = None
) -> Dict[str, Any]:
    """중복 탐지 결과를 JSON 직렬화 가능한 딕셔너리로 변환.

    Args:
        results: 중복 그룹 결과 리스트.
        file_data_store: 파일 데이터 저장소 (선택적, 파일 정보 조회용).
        folder_path: 스캔 폴더 경로 (선택적).

    Returns:
        JSON 직렬화 가능한 딕셔너리.
    """
    # 중복 그룹 리스트 직렬화
    groups: List[Dict[str, Any]] = []

    for result in results:
        # 그룹 기본 정보
        group_dict: Dict[str, Any] = {
            "group_id": result.group_id,
            "duplicate_type": result.duplicate_type,
            "file_count": len(result.file_ids),
            "confidence": result.confidence,
            "recommended_keeper_id": result.recommended_keeper_id,
        }

        # 파일 정보 직렬화
        files_info: List[Dict[str, Any]] = []
        for file_id in result.file_ids:
            file_info: Dict[str, Any] = {
                "file_id": file_id,
                "is_canonical": (
                    (file_id == result.recommended_keeper_id)
                    if result.recommended_keeper_id
                    else False
                ),
            }

            # FileDataStore에서 파일 상세 정보 조회
            if file_data_store:
                file_data = file_data_store.get_file(file_id)
                if file_data:
                    file_info.update(
                        {
                            "path": str(file_data.path),
                            "size": file_data.size,
                            "mtime": (
                                file_data.mtime.isoformat()
                                if isinstance(file_data.mtime, datetime)
                                else str(file_data.mtime)
                            ),
                            "extension": file_data.extension,
                            "similarity_score": file_data.similarity_score,
                        }
                    )

            files_info.append(file_info)

        group_dict["files"] = files_info

        # Evidence 정보 직렬화 (있으면)
        if result.evidence:
            # evidence의 파일별 정보는 files_info에 병합되므로
            # 메타 정보만 포함
            evidence_dict: Dict[str, Any] = {}
            for key, value in result.evidence.items():
                # files 키는 이미 파일 정보에 병합되므로 제외
                if key != "files":
                    # datetime 객체 등 JSON 직렬화 불가능한 타입 처리
                    if isinstance(value, datetime):
                        evidence_dict[key] = value.isoformat()
                    elif isinstance(value, (str, int, float, bool, type(None))):
                        evidence_dict[key] = value
                    elif isinstance(value, (list, dict)):
                        # 재귀적으로 직렬화 가능한 타입만 포함
                        try:
                            json.dumps(value)
                            evidence_dict[key] = value
                        except (TypeError, ValueError):
                            evidence_dict[key] = str(value)
                    else:
                        evidence_dict[key] = str(value)

            if evidence_dict:
                group_dict["evidence"] = evidence_dict

        groups.append(group_dict)

    # 탐지 정보 구성
    # total_scanned_files: 스캔된 실제 파일 수
    total_scanned_files = 0
    if file_data_store:
        total_scanned_files = file_data_store.get_file_count()

    # total_unique_files_in_groups: 그룹에 포함된 유니크 파일 수
    unique_file_ids: set[int] = set()
    for result in results:
        unique_file_ids.update(result.file_ids)
    total_unique_files_in_groups = len(unique_file_ids)

    # total_file_occurrences_in_groups: 그룹 내 파일 엔트리 총합 (정규화 전 값)
    total_file_occurrences_in_groups = sum(len(result.file_ids) for result in results)

    # files_without_duplicates: 중복 그룹에 포함되지 않은 파일 수
    files_without_duplicates = max(0, total_scanned_files - total_unique_files_in_groups)

    detection_info: Dict[str, Any] = {
        "detection_timestamp": datetime.now().isoformat(),
        "folder_path": str(folder_path) if folder_path else None,
        "total_groups": len(results),
        # 하위 호환성: total_files는 total_scanned_files와 동일한 값으로 설정
        "total_files": total_scanned_files,
        "total_scanned_files": total_scanned_files,
        "total_unique_files_in_groups": total_unique_files_in_groups,
        "total_file_occurrences_in_groups": total_file_occurrences_in_groups,
        "files_without_duplicates": files_without_duplicates,
    }

    return {
        "detection_info": detection_info,
        "groups": groups,
    }


def save_duplicate_result_to_json(
    results: List[DuplicateGroupResult],
    output_path: Path,
    file_data_store=None,
    folder_path: Optional[Path] = None,
) -> None:
    """중복 탐지 결과를 JSON 파일로 저장.

    Args:
        results: 중복 그룹 결과 리스트.
        output_path: 저장할 JSON 파일 경로.
        file_data_store: 파일 데이터 저장소 (선택적, 파일 정보 조회용).
        folder_path: 스캔 폴더 경로 (선택적).

    Raises:
        OSError: 파일 쓰기 실패 시.
        ValueError: 직렬화 실패 시.
    """
    try:
        # 출력 디렉토리가 없으면 생성
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # 딕셔너리로 변환
        data = serialize_duplicate_result_to_json(results, file_data_store, folder_path)

        # JSON 파일로 저장
        with open(output_path, "w", encoding=Constants.DEFAULT_ENCODING) as f:
            json.dump(data, f, indent=2, ensure_ascii=False, sort_keys=True)

        logger.info(f"중복 탐지 결과를 JSON 파일로 저장했습니다: {output_path}")

    except OSError as e:
        error_msg = f"중복 탐지 결과 JSON 파일 저장 실패 (파일 시스템 오류): {output_path} - {e}"
        logger.error(error_msg)
        raise OSError(error_msg) from e

    except (ValueError, TypeError) as e:
        error_msg = f"중복 탐지 결과 JSON 직렬화 실패: {e}"
        logger.error(error_msg)
        raise ValueError(error_msg) from e

    except Exception as e:
        error_msg = f"중복 탐지 결과 JSON 저장 중 예상치 못한 오류: {output_path} - {e}"
        logger.error(error_msg, exc_info=True)
        raise


@dataclass(frozen=True)
class DuplicateDetectionSummary:
    """Lightweight stats from a saved duplicate_results_*.json detection_info block."""

    total_groups: int
    duplicate_move_count: int
    detection_timestamp: Optional[str]
    folder_path: str


def _normalize_folder_key(path: str | Path) -> str:
    try:
        return str(Path(path).resolve()).casefold()
    except OSError:
        return str(path).casefold()


def default_duplicate_save_dir() -> Path:
    """Project ``SAVE/`` directory for duplicate JSON exports."""
    return Path(__file__).resolve().parents[3] / "SAVE"


def find_latest_duplicate_summary(
    folder_path: Path,
    *,
    save_dir: Optional[Path] = None,
) -> Optional[DuplicateDetectionSummary]:
    """Return stats from the newest duplicate JSON for ``folder_path``, if any."""
    root = save_dir or default_duplicate_save_dir()
    if not root.is_dir():
        return None

    target_key = _normalize_folder_key(folder_path)
    candidates: list[tuple[float, Path]] = []
    for path in root.glob("duplicate_results_*.json"):
        try:
            candidates.append((_duplicate_json_sort_key(path), path))
        except OSError:
            continue
    candidates.sort(key=lambda item: item[0], reverse=True)

    for _, json_path in candidates:
        summary = _read_duplicate_summary(json_path, target_key)
        if summary is not None:
            return summary
    return None


def _duplicate_json_sort_key(path: Path) -> float:
    """Prefer filename timestamp, fall back to file mtime."""
    mtime = path.stat().st_mtime
    stem = path.stem
    if stem.startswith("duplicate_results_"):
        ts_text = stem.removeprefix("duplicate_results_")
        try:
            parsed = datetime.strptime(ts_text, "%Y%m%d_%H%M%S")
            return max(mtime, parsed.timestamp())
        except ValueError:
            pass
    return mtime


def _read_duplicate_summary(
    json_path: Path,
    target_folder_key: str,
) -> Optional[DuplicateDetectionSummary]:
    try:
        with open(json_path, encoding=Constants.DEFAULT_ENCODING) as handle:
            payload = json.load(handle)
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        logger.debug("Skipping unreadable duplicate JSON: %s", json_path)
        return None

    info = payload.get("detection_info")
    if not isinstance(info, dict):
        return None

    saved_folder = info.get("folder_path")
    if not saved_folder or _normalize_folder_key(str(saved_folder)) != target_folder_key:
        return None

    total_groups = int(info.get("total_groups") or 0)
    unique_in_groups = int(info.get("total_unique_files_in_groups") or 0)
    move_count = max(0, unique_in_groups - total_groups)

    return DuplicateDetectionSummary(
        total_groups=total_groups,
        duplicate_move_count=move_count,
        detection_timestamp=info.get("detection_timestamp"),
        folder_path=str(saved_folder),
    )


def generate_duplicate_json_filename(detection_timestamp: Optional[datetime] = None) -> str:
    """중복 탐지 결과 JSON 파일명 생성.

    Args:
        detection_timestamp: 탐지 타임스탬프. None이면 현재 시간 사용.

    Returns:
        파일명 (예: "duplicate_results_20260108_234959.json").
    """
    if detection_timestamp is None:
        detection_timestamp = datetime.now()

    # 형식: duplicate_results_YYYYMMDD_HHMMSS.json
    timestamp_str = detection_timestamp.strftime("%Y%m%d_%H%M%S")
    return f"duplicate_results_{timestamp_str}.json"
