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
    scan_state: str,
    scan_last_run: str | None,
    has_pending_apply: bool,
    connection: str = "Library session (Python)",
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
            "duplicateGroups": 0,
            "integrityIssues": 0,
            "lastRun": scan_last_run,
            "scanOptions": [".txt", ".md", "하위 폴더 포함"],
        },
        "pipeline": {
            "phase": pipeline_phase,
            "percent": pipeline_percent,
            "label": pipeline_label,
            "cancellable": pipeline_cancellable,
        },
        "work": {
            "activeMode": active_mode,
            "scan": {"state": scan_state, "lastRun": scan_last_run},
            "resolve": {
                "queueCount": 0,
                "groupCount": 0,
                "conflictCount": 0,
                "approvedCount": 0,
                "hasPendingApply": has_pending_apply,
                "libraryRevision": library_revision,
            },
            "quality": {
                "integrityIssueCount": 0,
                "encodingIssueCount": 0,
                "smallFileAnomalyCount": 0,
            },
        },
        "fileListSummary": {
            "totalCount": file_count,
            "filteredCount": file_count,
            "issueCount": 0,
            "selectedCount": 0,
        },
    }
