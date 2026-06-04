"""Finalize blocker and warning rules (PR-23)."""

from __future__ import annotations

from typing import Any

_UNRESOLVED_STATUSES = frozenset({"unreviewed", "conflict"})

_BLOCKER_MESSAGES: dict[str, str] = {
    "PENDING_MOVE_PREVIEW": "이동 미리보기가 적용되지 않았거나 해제되지 않았습니다.",
    "PENDING_REPAIR_PREVIEW": "품질 복구 미리보기가 적용되지 않았거나 해제되지 않았습니다.",
    "SCAN_NOT_SUCCESS": "스캔이 성공적으로 완료되지 않았습니다.",
    "UNRESOLVED_DUPLICATE_QUEUE": "미해결 exact 중복 파일이 남아 있습니다.",
    "QUALITY_INTEGRITY_ISSUES": "읽기 실패 등 무결성 품질 오류가 남아 있습니다.",
}

_WARNING_MESSAGES: dict[str, str] = {
    "ENCODING_QUALITY_ISSUES": "UTF-8이 아닌 인코딩(또는 디코드 경고) 파일이 남아 있습니다.",
    "SMALL_FILE_ANOMALIES": "소용량 파일 이상이 남아 있습니다.",
    "UNREVIEWED_RELATION": "미검토 relation 파일이 남아 있습니다.",
    "NEAR_GROUPS_PRESENT": "미검토 near 중복 파일이 남아 있습니다.",
}


def count_unresolved_file_rows(rows: list[dict[str, Any]], row_type: str) -> int:
    count = 0
    for row in rows:
        if row.get("rowKind") != "file":
            continue
        if row.get("type") != row_type:
            continue
        if row.get("status") in _UNRESOLVED_STATUSES:
            count += 1
    return count


def exact_unresolved_queue_count(rows: list[dict[str, Any]]) -> int:
    return count_unresolved_file_rows(rows, "exact")


def near_unresolved_file_row_count(rows: list[dict[str, Any]]) -> int:
    return count_unresolved_file_rows(rows, "near")


def relation_unresolved_file_row_count(rows: list[dict[str, Any]]) -> int:
    return count_unresolved_file_rows(rows, "relation")


def _blocker(code: str, *, count: int | None = None) -> dict[str, Any]:
    entry: dict[str, Any] = {"code": code, "message": _BLOCKER_MESSAGES[code]}
    if count is not None:
        entry["count"] = count
    return entry


def _warning(code: str, *, count: int) -> dict[str, Any]:
    return {"code": code, "message": _WARNING_MESSAGES[code], "count": count}


def compute_finalize_blockers(
    *,
    review_rows: list[dict[str, Any]],
    scan_state: str,
    has_pending_apply: bool,
    has_pending_quality_repair: bool,
    encoding_issue_count: int,
    integrity_issue_count: int,
) -> list[dict[str, Any]]:
    blockers: list[dict[str, Any]] = []
    if has_pending_apply:
        blockers.append(_blocker("PENDING_MOVE_PREVIEW"))
    if has_pending_quality_repair:
        blockers.append(_blocker("PENDING_REPAIR_PREVIEW"))
    if scan_state != "success":
        blockers.append(_blocker("SCAN_NOT_SUCCESS"))
    exact_queue = exact_unresolved_queue_count(review_rows)
    if exact_queue > 0:
        blockers.append(_blocker("UNRESOLVED_DUPLICATE_QUEUE", count=exact_queue))
    if integrity_issue_count > 0:
        blockers.append(_blocker("QUALITY_INTEGRITY_ISSUES", count=integrity_issue_count))
    return blockers


def compute_finalize_warnings(
    *,
    review_rows: list[dict[str, Any]],
    small_file_anomaly_count: int,
    encoding_issue_count: int = 0,
) -> list[dict[str, Any]]:
    warnings: list[dict[str, Any]] = []
    if encoding_issue_count > 0:
        warnings.append(_warning("ENCODING_QUALITY_ISSUES", count=encoding_issue_count))
    if small_file_anomaly_count > 0:
        warnings.append(_warning("SMALL_FILE_ANOMALIES", count=small_file_anomaly_count))
    relation_count = relation_unresolved_file_row_count(review_rows)
    if relation_count > 0:
        warnings.append(_warning("UNREVIEWED_RELATION", count=relation_count))
    near_count = near_unresolved_file_row_count(review_rows)
    if near_count > 0:
        warnings.append(_warning("NEAR_GROUPS_PRESENT", count=near_count))
    return warnings


def finalize_result_status(
    blockers: list[dict[str, Any]],
    warnings: list[dict[str, Any]],
) -> str:
    if blockers:
        return "blocked"
    if warnings:
        return "complete_with_warnings"
    return "complete"
