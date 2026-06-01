"""Minimal pywebview js_api stub for UI smoke tests."""

from __future__ import annotations

import json
from typing import Any
from uuid import uuid4

from app.bridge_contract import (
    PreviewApplyError,
    clamp_query_limit,
    validate_app_snapshot,
    validate_move_preview,
    validate_quality_rows_page,
    validate_review_rows_page,
    validate_selection_scope,
)
from app.selection_fingerprint import selection_fingerprint


class BridgeApi:
    """Expose methods to ``window.pywebview.api`` (snake_case)."""

    def __init__(self) -> None:
        self._active_mode = "resolve"
        self._folder = "D:/Novels/Library/raw"
        self._library_revision = 0
        self._has_pending_apply = False
        self._pending_apply: dict[str, Any] | None = None

    def _resolve_block(self) -> dict[str, Any]:
        return {
            "queueCount": 412,
            "groupCount": 37,
            "conflictCount": 3,
            "approvedCount": 126,
            "hasPendingApply": self._has_pending_apply,
            "libraryRevision": self._library_revision,
        }

    def get_snapshot(self) -> dict[str, Any]:
        payload = {
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
                "resolve": self._resolve_block(),
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
        validate_app_snapshot(payload)
        return payload

    def set_work_mode(self, mode: str) -> None:
        self._active_mode = mode

    def select_folder(self) -> None:
        self._folder = "D:/Novels/Library/selected"

    def start_scan(self, options: dict[str, Any] | None = None) -> None:
        _ = options

    def cancel_run(self) -> None:
        return None

    def query_review_rows(self, query: dict[str, Any]) -> dict[str, Any]:
        limit = clamp_query_limit(query)
        _ = limit
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
        payload = {
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
        validate_review_rows_page(payload)
        return payload

    def query_quality_rows(self, query: dict[str, Any]) -> dict[str, Any]:
        _ = clamp_query_limit(query)
        payload = {
            "rows": [],
            "pageInfo": {
                "cursor": None,
                "nextCursor": None,
                "hasMore": False,
                "totalFiltered": 0,
            },
            "summary": {"issueCount": 0, "warningCount": 0, "errorCount": 0},
        }
        validate_quality_rows_page(payload)
        return payload

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
        validate_selection_scope(selection)
        token = f"preview-{uuid4()}"
        fp = selection_fingerprint(selection)
        rev = self._library_revision
        self._pending_apply = {
            "token": token,
            "fingerprint": fp,
            "library_revision": rev,
        }
        self._has_pending_apply = True
        payload: dict[str, Any] = {
            "previewToken": token,
            "libraryRevision": rev,
            "selectionFingerprint": fp,
            "hasPendingApply": True,
            "rows": [{"id": "row-1", "action": "move_organized"}],
            "summary": {"rowCount": 1},
        }
        validate_move_preview(payload)
        return payload

    def _validate_apply(self, payload: dict[str, Any]) -> tuple[dict[str, Any], str]:
        token = (payload.get("previewToken") or "").strip()
        if not token:
            raise PreviewApplyError("MISSING_PREVIEW_TOKEN")
        selection = payload.get("selection")
        if not isinstance(selection, dict):
            raise PreviewApplyError("INVALID_PREVIEW_TOKEN", "selection required")
        validate_selection_scope(selection)
        pending = self._pending_apply
        if not pending:
            raise PreviewApplyError("NO_PENDING_APPLY")
        if token != pending.get("token"):
            raise PreviewApplyError("INVALID_PREVIEW_TOKEN")
        if self._library_revision != pending.get("library_revision"):
            raise PreviewApplyError("STALE_PREVIEW")
        fp = selection_fingerprint(selection)
        if fp != pending.get("fingerprint"):
            raise PreviewApplyError("SELECTION_CHANGED")
        return selection, token

    def apply_resolved_actions(self, payload: dict[str, Any]) -> None:
        self._validate_apply(payload)
        self._pending_apply = None
        self._has_pending_apply = False

    def discard_move_preview(self, payload: dict[str, Any]) -> None:
        token = (payload.get("previewToken") or "").strip()
        pending = self._pending_apply
        if pending and token and token == pending.get("token"):
            self._pending_apply = None
        self._has_pending_apply = False

    def query_review_rows_json(self, query_json: str) -> str:
        """Optional helper if JS passes JSON string."""
        return json.dumps(self.query_review_rows(json.loads(query_json)))
