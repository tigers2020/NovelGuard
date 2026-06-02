"""Canonical pywebview js_api method names (mirror web/src/contracts/bridgeParity.ts)."""

from __future__ import annotations

PYWEBVIEW_API_METHODS: tuple[str, ...] = (
    "get_snapshot",
    "select_folder",
    "start_scan",
    "cancel_run",
    "set_work_mode",
    "query_review_rows",
    "query_quality_rows",
    "get_duplicate_group_detail",
    "get_quality_issue_detail",
    "get_move_preview",
    "apply_resolved_actions",
    "discard_move_preview",
    "update_review_decisions",
    "get_app_setting",
    "set_app_setting",
)
