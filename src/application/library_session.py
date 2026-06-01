"""Library orchestration for pywebview bridge (PR-14a/14b)."""

from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Any

from application.dto_mapper import (
    build_snapshot,
    scan_timestamp,
)
from application.ports.library_index import LibraryIndexPort
from application.quality_analyzer import analyze_quality
from application.quality_query import query_quality_page
from application.quality_rows_builder import build_quality_rows
from application.review_query import query_review_page
from application.review_rows_builder import build_review_rows
from domain.duplicate_exact import find_exact_duplicate_groups
from domain.models import FileRecord

_MAX_QUERY_LIMIT = 200
_DEFAULT_QUERY_LIMIT = 100


class LibrarySession:
    def __init__(
        self,
        index: LibraryIndexPort,
        *,
        scan_folder: Callable[..., None],
    ) -> None:
        self._lock = threading.RLock()
        self._index = index
        self._scan_folder = scan_folder
        self._library_revision = 0
        self._active_mode = "resolve"
        self._pipeline_running = False
        self._pipeline_phase = "idle"
        self._pipeline_percent = 0
        self._pipeline_label = "대기 중"
        self._pipeline_cancellable = False
        self._scan_state = "empty"
        self._scan_last_run: str | None = None
        self._cancel_requested = False
        self._scan_thread: threading.Thread | None = None
        self._backup_files: list[FileRecord] | None = None
        self._backup_folder: str | None = None
        self._has_pending_apply = False
        self._review_rows_cache: list[dict[str, Any]] = []
        self._duplicate_group_count = 0
        self._queue_count = 0
        self._files_by_id: dict[str, FileRecord] = {}
        self._quality_rows_cache: list[dict[str, Any]] = []
        self._integrity_issue_count = 0
        self._encoding_issue_count = 0
        self._small_file_anomaly_count = 0
        self._total_quality_issue_count = 0

    def select_folder(self, path: str | None = None) -> None:
        folder = path
        if folder is None:
            try:
                import tkinter as tk
                from tkinter import filedialog
            except ImportError as exc:
                raise RuntimeError("Folder picker requires tkinter") from exc
            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)
            try:
                picked = filedialog.askdirectory(title="스캔 폴더 선택")
            finally:
                root.destroy()
            if not picked:
                return
            folder = picked

        with self._lock:
            self._index.replace_files(folder, [])
            self._index.replace_quality_issues(folder, [])
            self._library_revision += 1
            self._scan_state = "ready"
            self._scan_last_run = None
            self._pipeline_phase = "idle"
            self._pipeline_percent = 0
            self._pipeline_label = "대기 중"
            self._pipeline_cancellable = False
            self._backup_files = None
            self._backup_folder = None
            self._clear_review_cache()

    def start_scan(self, options: dict[str, Any] | None = None) -> None:
        _ = options
        with self._lock:
            folder = self._index.folder_path
            if not folder or self._pipeline_running:
                return
            self._backup_files = self._index.files()
            self._backup_folder = folder
            self._cancel_requested = False
            self._pipeline_running = True
            self._pipeline_phase = "scan"
            self._pipeline_percent = 0
            self._pipeline_label = "스캔 준비"
            self._pipeline_cancellable = True
            self._scan_state = "running"
            self._scan_thread = threading.Thread(target=self._run_scan, args=(folder,), daemon=True)
            self._scan_thread.start()

    def cancel_run(self) -> None:
        with self._lock:
            if not self._pipeline_running:
                return
            self._cancel_requested = True

    def set_work_mode(self, mode: str) -> None:
        with self._lock:
            if mode in ("scan", "resolve", "quality"):
                self._active_mode = mode

    def get_snapshot(self) -> dict[str, Any]:
        with self._lock:
            return build_snapshot(
                folder_path=self._index.folder_path,
                file_count=self._index.file_count(),
                total_bytes=self._index.total_bytes(),
                library_revision=self._library_revision,
                active_mode=self._active_mode,
                pipeline_phase=self._pipeline_phase,
                pipeline_percent=self._pipeline_percent,
                pipeline_label=self._pipeline_label,
                pipeline_cancellable=self._pipeline_cancellable,
                scan_state=self._scan_state,
                scan_last_run=self._scan_last_run,
                has_pending_apply=self._has_pending_apply,
                duplicate_group_count=self._duplicate_group_count,
                queue_count=self._queue_count,
                integrity_issue_count=self._integrity_issue_count,
                encoding_issue_count=self._encoding_issue_count,
                small_file_anomaly_count=self._small_file_anomaly_count,
                total_quality_issue_count=self._total_quality_issue_count,
            )

    def query_review_rows(self, query: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            limit = _clamp_query_limit(query)
            return query_review_page(self._review_rows_cache, query, limit=limit)

    def query_quality_rows(self, query: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            limit = _clamp_query_limit(query)
            return query_quality_page(self._quality_rows_cache, query, limit=limit)

    def get_duplicate_group_detail(self, group_id: str) -> dict[str, Any]:
        with self._lock:
            groups = find_exact_duplicate_groups(list(self._files_by_id.values()))
            target = next((g for g in groups if g.group_id == group_id), None)
            if not target:
                return {"groupId": group_id, "members": []}
            members = [
                {
                    "id": mid,
                    "name": self._files_by_id[mid].name,
                    "path": self._files_by_id[mid].relative_path,
                    "isKeeper": mid == target.keeper_id,
                }
                for mid in target.member_ids
                if mid in self._files_by_id
            ]
            return {"groupId": group_id, "members": members}

    def get_quality_issue_detail(self, issue_id: str) -> dict[str, Any]:
        return {
            "id": issue_id,
            "issueType": "integrity",
            "name": "sample",
            "integrity": "Read error",
        }

    def library_revision(self) -> int:
        with self._lock:
            return self._library_revision

    def set_has_pending_apply(self, value: bool) -> None:
        with self._lock:
            self._has_pending_apply = value

    def first_file_id(self) -> str | None:
        with self._lock:
            files = self._index.files()
            return files[0].id if files else None

    def _clear_review_cache(self) -> None:
        self._review_rows_cache = []
        self._duplicate_group_count = 0
        self._queue_count = 0
        self._files_by_id = {}
        self._clear_quality_cache()

    def _clear_quality_cache(self) -> None:
        self._quality_rows_cache = []
        self._integrity_issue_count = 0
        self._encoding_issue_count = 0
        self._small_file_anomaly_count = 0
        self._total_quality_issue_count = 0

    def _rebuild_review_index(self, files: list[FileRecord]) -> None:
        self._files_by_id = {f.id: f for f in files}
        groups = find_exact_duplicate_groups(files)
        self._review_rows_cache = build_review_rows(groups, self._files_by_id)
        self._duplicate_group_count = len(groups)
        self._queue_count = len(self._review_rows_cache)

    def _rebuild_quality_index(self, folder: str, files: list[FileRecord]) -> None:
        issues = analyze_quality(folder, files)
        self._index.replace_quality_issues(folder, issues)
        self._quality_rows_cache = build_quality_rows(issues, self._files_by_id)
        self._integrity_issue_count = sum(
            1 for row in self._quality_rows_cache if row.get("issueType") == "integrity"
        )
        self._encoding_issue_count = sum(
            1 for row in self._quality_rows_cache if row.get("issueType") == "encoding"
        )
        self._small_file_anomaly_count = sum(
            1 for row in self._quality_rows_cache if row.get("issueType") == "small_file"
        )
        self._total_quality_issue_count = len(self._quality_rows_cache)

    def _run_scan(self, folder: str) -> None:
        collected: list[FileRecord] = []
        scan_error: str | None = None

        def on_progress(pct: int, label: str) -> None:
            with self._lock:
                self._pipeline_percent = pct
                self._pipeline_label = label

        def cancel_check() -> bool:
            return self._cancel_requested

        try:
            self._scan_folder(
                folder,
                on_progress=on_progress,
                cancel_check=cancel_check,
                out=collected.append,
            )
        except Exception as exc:
            scan_error = str(exc)

        with self._lock:
            self._pipeline_running = False
            self._pipeline_cancellable = False
            self._scan_thread = None

            if scan_error is not None:
                self._restore_backup_after_failed_scan(folder)
                self._pipeline_phase = "idle"
                self._pipeline_percent = 0
                self._pipeline_label = "오류"
                self._scan_state = "error"
                return

            if self._cancel_requested:
                self._restore_backup_after_cancel(folder)
                self._pipeline_phase = "idle"
                self._pipeline_percent = 0
                had_prior = bool(self._backup_files)
                self._pipeline_label = "대기 중" if had_prior else "취소됨"
                self._scan_state = "success" if had_prior else "error"
                return

            self._index.replace_files(folder, collected)
            self._rebuild_review_index(collected)
            self._rebuild_quality_index(folder, collected)
            self._scan_state = "success"
            self._scan_last_run = scan_timestamp()
            self._library_revision += 1
            self._pipeline_phase = "idle"
            self._pipeline_percent = 100
            self._pipeline_label = "대기 중"
            self._backup_files = None
            self._backup_folder = None

    def _restore_backup_after_cancel(self, folder: str) -> None:
        if self._backup_files is not None and self._backup_folder:
            self._index.replace_files(self._backup_folder, self._backup_files)
            self._rebuild_review_index(self._backup_files)
            self._rebuild_quality_index(self._backup_folder, self._backup_files)
        else:
            self._index.replace_files(folder, [])
            self._index.replace_quality_issues(folder, [])
            self._clear_review_cache()

    def _restore_backup_after_failed_scan(self, folder: str) -> None:
        if self._backup_files is not None and self._backup_folder:
            self._index.replace_files(self._backup_folder, self._backup_files)
            self._rebuild_review_index(self._backup_files)
            self._rebuild_quality_index(self._backup_folder, self._backup_files)
            self._scan_state = "success"
            self._pipeline_label = "대기 중"
        else:
            self._index.replace_files(folder, [])
            self._index.replace_quality_issues(folder, [])
            self._clear_review_cache()
            self._scan_state = "error"


def _clamp_query_limit(query: dict[str, Any]) -> int:
    raw = query.get("limit", _DEFAULT_QUERY_LIMIT)
    try:
        value = int(raw)
    except (TypeError, ValueError):
        value = _DEFAULT_QUERY_LIMIT
    return min(max(1, value), _MAX_QUERY_LIMIT)
