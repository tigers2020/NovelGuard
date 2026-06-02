"""Build finalize summary DTO (PR-23)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from application.finalize_audit_tail import read_audit_tail
from application.finalize_blockers import (
    compute_finalize_blockers,
    compute_finalize_warnings,
    exact_unresolved_queue_count,
)


def unique_file_ids_from_quality_issues(issues: list[Any]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for issue in issues:
        file_id = getattr(issue, "file_id", None)
        if not isinstance(file_id, str) or not file_id or file_id in seen:
            continue
        seen.add(file_id)
        ordered.append(file_id)
    return ordered


def build_finalize_summary(
    *,
    library_revision: int,
    scan_state: str,
    review_rows: list[dict[str, Any]],
    queue_count: int,
    conflict_count: int,
    approved_count: int,
    has_pending_apply: bool,
    has_pending_quality_repair: bool,
    encoding_issue_count: int,
    integrity_issue_count: int,
    small_file_anomaly_count: int,
    audit_log_path: Path,
) -> dict[str, Any]:
    blockers = compute_finalize_blockers(
        review_rows=review_rows,
        scan_state=scan_state,
        has_pending_apply=has_pending_apply,
        has_pending_quality_repair=has_pending_quality_repair,
        encoding_issue_count=encoding_issue_count,
        integrity_issue_count=integrity_issue_count,
    )
    warnings = compute_finalize_warnings(
        review_rows=review_rows,
        small_file_anomaly_count=small_file_anomaly_count,
    )
    return {
        "libraryRevision": library_revision,
        "scanState": scan_state,
        "resolve": {
            "queueCount": queue_count,
            "exactUnresolvedQueueCount": exact_unresolved_queue_count(review_rows),
            "conflictCount": conflict_count,
            "approvedCount": approved_count,
            "hasPendingApply": has_pending_apply,
        },
        "quality": {
            "encodingIssueCount": encoding_issue_count,
            "integrityIssueCount": integrity_issue_count,
            "smallFileAnomalyCount": small_file_anomaly_count,
            "hasPendingQualityRepair": has_pending_quality_repair,
        },
        "auditTail": read_audit_tail(audit_log_path),
        "blockers": blockers,
        "warnings": warnings,
    }
