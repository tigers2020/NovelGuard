"""Library orchestration for pywebview bridge (PR-14a)."""

from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Any

from application.dto_mapper import (
    build_snapshot,
    empty_quality_page,
    empty_review_page,
    scan_timestamp,
)
from application.ports.library_index import LibraryIndexPort
from domain.models import FileRecord


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
            self._library_revision += 1
            self._scan_state = "ready"
            self._scan_last_run = None
            self._pipeline_phase = "idle"
            self._pipeline_percent = 0
            self._pipeline_label = "대기 중"
            self._pipeline_cancellable = False
            self._backup_files = None
            self._backup_folder = None

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
            )

    def query_review_rows(self, query: dict[str, Any]) -> dict[str, Any]:
        _ = query
        with self._lock:
            return empty_review_page()

    def query_quality_rows(self, query: dict[str, Any]) -> dict[str, Any]:
        _ = query
        with self._lock:
            return empty_quality_page()

    def get_duplicate_group_detail(self, group_id: str) -> dict[str, Any]:
        return {"groupId": group_id}

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
        else:
            self._index.replace_files(folder, [])

    def _restore_backup_after_failed_scan(self, folder: str) -> None:
        if self._backup_files is not None and self._backup_folder:
            self._index.replace_files(self._backup_folder, self._backup_files)
            self._scan_state = "success"
            self._pipeline_label = "대기 중"
        else:
            self._index.replace_files(folder, [])
            self._scan_state = "error"
