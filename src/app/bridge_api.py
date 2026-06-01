"""Minimal pywebview js_api stub for UI smoke tests."""

from __future__ import annotations

import json
from typing import Any


class BridgeApi:
    """Expose methods to ``window.pywebview.api`` (snake_case)."""

    def __init__(self) -> None:
        self._active_mode = "resolve"
        self._folder = "D:/Novels/Library/raw"

    def get_snapshot(self) -> dict[str, Any]:
        return {
            "route": "work",
            "theme": "dark",
            "locale": "ko-KR",
            "connection": "Bridge ready (Python stub)",
            "library": {
                "folderPath": self._folder,
                "fileCount": 1284,
                "totalBytes": 2_840_000_000,
                "duplicateGroups": 37,
                "integrityIssues": 12,
                "lastRun": "2026-06-01 10:42",
                "scanOptions": [".txt", "하위 폴더 포함"],
            },
            "pipeline": {
                "phase": "idle",
                "percent": 0,
                "label": "대기 중",
                "cancellable": False,
            },
            "work": {
                "activeMode": self._active_mode,
                "scan": {"state": "success", "lastRun": "2026-06-01 10:42"},
                "resolve": {
                    "queueCount": 412,
                    "groupCount": 37,
                    "conflictCount": 3,
                    "approvedCount": 126,
                    "hasPendingApply": False,
                },
                "quality": {
                    "integrityIssueCount": 8,
                    "encodingIssueCount": 4,
                    "smallFileAnomalyCount": 0,
                },
            },
            "fileListSummary": {
                "totalCount": 1284,
                "filteredCount": 1284,
                "issueCount": 12,
                "selectedCount": 0,
            },
        }

    def set_work_mode(self, mode: str) -> None:
        self._active_mode = mode

    def select_folder(self) -> None:
        self._folder = "D:/Novels/Library/selected"

    def start_scan(self, options: dict[str, Any] | None = None) -> None:
        _ = options

    def cancel_run(self) -> None:
        return None

    def query_review_rows(self, query: dict[str, Any]) -> dict[str, Any]:
        _ = query
        rows = [
            {
                "id": "row-1",
                "rowKind": "file",
                "status": "unreviewed",
                "type": "exact",
                "name": "sample.txt",
                "keeperLabel": "sample.txt",
                "proposedAction": "keep",
                "targetFolder": "duplicate/",
                "confidence": 88,
                "hasChildren": False,
            }
        ]
        return {
            "rows": rows,
            "pageInfo": {
                "cursor": None,
                "nextCursor": None,
                "hasMore": False,
                "totalFiltered": 1,
            },
            "summary": {
                "selectedCount": 0,
                "conflictCount": 0,
                "unreviewedCount": 1,
                "approvedCount": 0,
            },
        }

    def query_quality_rows(self, query: dict[str, Any]) -> dict[str, Any]:
        _ = query
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

    def get_duplicate_group_detail(self, group_id: str) -> dict[str, Any]:
        return {"groupId": group_id}

    def get_quality_issue_detail(self, issue_id: str) -> dict[str, Any]:
        return {
            "id": issue_id,
            "issueType": "integrity",
            "name": "sample",
            "integrity": "Read error",
        }

    def get_move_preview(self, selection: dict[str, Any]) -> dict[str, Any]:
        return {"rows": [{"selection": selection}]}

    def apply_resolved_actions(self, selection: dict[str, Any]) -> None:
        _ = selection

    def query_review_rows_json(self, query_json: str) -> str:
        """Optional helper if JS passes JSON string."""
        return json.dumps(self.query_review_rows(json.loads(query_json)))
