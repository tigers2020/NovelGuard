"""Map internal library state to PR-10 bridge DTO dicts."""

from __future__ import annotations

from datetime import datetime
from typing import Any


def empty_review_page() -> dict[str, Any]:
    return {
        "rows": [],
        "pageInfo": {
            "cursor": None,
            "nextCursor": None,
            "hasMore": False,
            "totalFiltered": 0,
        },
        "summary": {
            "selectedCount": 0,
            "conflictCount": 0,
            "unreviewedCount": 0,
            "approvedCount": 0,
        },
    }


def empty_file_rows_page(cursor: Any = None) -> dict[str, Any]:
    return {
        "rows": [],
        "pageInfo": {
            "cursor": cursor,
            "nextCursor": None,
            "hasMore": False,
            "totalFiltered": 0,
        },
    }


def empty_quality_page() -> dict[str, Any]:
    return {
        "rows": [],
        "pageInfo": {
            "cursor": None,
            "nextCursor": None,
            "hasMore": False,
            "totalFiltered": 0,
        },
        "summary": {"issueCount": 0, "warningCount": 0, "errorCount": 0},
    }


def scan_timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def build_snapshot(
    *,
    folder_path: str | None,
    file_count: int,
    total_bytes: int,
    library_revision: int,
    active_mode: str,
    pipeline_phase: str,
    pipeline_percent: int,
    pipeline_label: str,
    pipeline_cancellable: bool,
    pipeline_background: dict[str, Any] | None = None,
    scan_state: str,
    scan_last_run: str | None,
    index_ready: bool = False,
    deep_analysis_complete: bool = False,
    deep_analysis_status: str = "idle",
    deep_analysis_error: str | None = None,
    has_pending_apply: bool,
    duplicate_group_count: int = 0,
    queue_count: int = 0,
    approved_count: int = 0,
    conflict_count: int = 0,
    integrity_issue_count: int = 0,
    encoding_issue_count: int = 0,
    small_file_anomaly_count: int = 0,
    total_quality_issue_count: int = 0,
    has_pending_quality_repair: bool = False,
    finalize_last_report_id: str | None = None,
    finalize_last_status: str = "idle",
    finalize_last_run_at: str | None = None,
    finalize_blocker_count: int = 0,
    finalize_warning_count: int = 0,
    connection: str = "Library session (Python)",
    scan_options: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "route": "work",
        "theme": "dark",
        "locale": "ko-KR",
        "connection": connection,
        "library": {
            "folderPath": folder_path,
            "fileCount": file_count,
            "totalBytes": total_bytes,
            "duplicateGroups": duplicate_group_count,
            "integrityIssues": integrity_issue_count,
            "lastRun": scan_last_run,
            "scanOptions": scan_options or [".txt,.md", "하위 폴더 포함", "숨김 제외"],
        },
        "pipeline": {
            "phase": pipeline_phase,
            "percent": pipeline_percent,
            "label": pipeline_label,
            "cancellable": pipeline_cancellable,
            "background": pipeline_background,
        },
        "work": {
            "activeMode": active_mode,
            "scan": {
                "state": scan_state,
                "lastRun": scan_last_run,
                "indexReady": index_ready,
                "deepAnalysisComplete": deep_analysis_complete,
                "deepAnalysisStatus": deep_analysis_status,
                "deepAnalysisError": deep_analysis_error,
            },
            "resolve": {
                "queueCount": queue_count,
                "groupCount": duplicate_group_count,
                "conflictCount": conflict_count,
                "approvedCount": approved_count,
                "hasPendingApply": has_pending_apply,
                "libraryRevision": library_revision,
            },
            "quality": {
                "integrityIssueCount": integrity_issue_count,
                "encodingIssueCount": encoding_issue_count,
                "smallFileAnomalyCount": small_file_anomaly_count,
                "hasPendingQualityRepair": has_pending_quality_repair,
            },
            "finalize": {
                "lastReportId": finalize_last_report_id,
                "lastStatus": finalize_last_status,
                "lastRunAt": finalize_last_run_at,
                "blockerCount": finalize_blocker_count,
                "warningCount": finalize_warning_count,
            },
        },
        "fileListSummary": {
            "totalCount": file_count,
            "filteredCount": file_count,
            "issueCount": total_quality_issue_count,
            "selectedCount": 0,
        },
    }
