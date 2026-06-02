"""Library orchestration for pywebview bridge (PR-14a/14b)."""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any

from application.app_settings import AppSettings
from application.dto_mapper import (
    build_snapshot,
    scan_timestamp,
)
from application.ports.library_index import LibraryIndexPort
from application.quality_analyzer import analyze_quality
from application.quality_issue_detail import build_quality_issue_detail
from application.quality_query import query_quality_page
from application.quality_rows_builder import build_quality_rows
from application.review_query import query_review_page
from application.review_rows_builder import build_review_rows
from application.review_snapshot_counts import file_row_status_counts
from application.review_state_merge import rebuild_rows_with_review_state
from domain.duplicate_exact import find_exact_duplicate_groups
from domain.duplicate_near import NearDuplicateGroup
from domain.filename_relation import RelationGroup
from domain.models import FileRecord
from domain.settings_keys import SETTINGS_KEY_INCLUDE_RELATION

_MAX_QUERY_LIMIT = 200
_DEFAULT_QUERY_LIMIT = 100
_LOGGER = logging.getLogger(__name__)


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
        self._approved_count = 0
        self._conflict_count = 0
        self._files_by_id: dict[str, FileRecord] = {}
        self._quality_rows_cache: list[dict[str, Any]] = []
        self._integrity_issue_count = 0
        self._encoding_issue_count = 0
        self._small_file_anomaly_count = 0
        self._total_quality_issue_count = 0
        self._apply_in_progress = False
        self._has_pending_quality_repair = False
        self._finalize_last_report_id: str | None = None
        self._finalize_last_status = "idle"
        self._finalize_last_run_at: str | None = None
        self._finalize_blocker_count = 0
        self._finalize_warning_count = 0
        self._finalize_last_report_path: str | None = None
        self._finalize_runner: Any = None
        self._near_groups_by_id: dict[str, NearDuplicateGroup] = {}
        self._relation_groups_by_id: dict[str, RelationGroup] = {}
        self._settings = AppSettings()

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
            self._index.clear_review_state(folder)
            self._index.clear_near_duplicate_results(folder)
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
            if not folder or self._pipeline_running or self._apply_in_progress:
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
            if mode in ("scan", "resolve", "quality", "finalize"):
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
                approved_count=self._approved_count,
                conflict_count=self._conflict_count,
                integrity_issue_count=self._integrity_issue_count,
                encoding_issue_count=self._encoding_issue_count,
                small_file_anomaly_count=self._small_file_anomaly_count,
                total_quality_issue_count=self._total_quality_issue_count,
                has_pending_quality_repair=self._has_pending_quality_repair,
                finalize_last_report_id=self._finalize_last_report_id,
                finalize_last_status=self._finalize_last_status,
                finalize_last_run_at=self._finalize_last_run_at,
                finalize_blocker_count=self._finalize_blocker_count,
                finalize_warning_count=self._finalize_warning_count,
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
        from application.duplicate_group_detail import (
            build_duplicate_group_detail,
            index_quality_rows_by_path,
        )
        from application.near_group_detail import build_near_group_detail

        with self._lock:
            quality_by_path = index_quality_rows_by_path(self._quality_rows_cache)
            if group_id.startswith("relation:"):
                from application.relation_group_detail import build_relation_group_detail

                relation_group = self._relation_groups_by_id.get(group_id)
                return build_relation_group_detail(
                    group_id,
                    relation_group=relation_group,
                    review_rows=self._review_rows_cache,
                    files_by_id=self._files_by_id,
                    quality_by_path=quality_by_path,
                )
            if group_id.startswith("near:"):
                near_group = self._near_groups_by_id.get(group_id)
                return build_near_group_detail(
                    group_id,
                    near_group=near_group,
                    review_rows=self._review_rows_cache,
                    files_by_id=self._files_by_id,
                    quality_by_path=quality_by_path,
                )
            return build_duplicate_group_detail(
                group_id,
                review_rows=self._review_rows_cache,
                files_by_id=self._files_by_id,
                quality_by_path=quality_by_path,
            )

    def get_quality_issue_detail(self, issue_id: str) -> dict[str, Any]:
        with self._lock:
            return build_quality_issue_detail(
                issue_id,
                quality_rows=self._quality_rows_cache,
                quality_issues=self._index.quality_issues(),
                files_by_id=self._files_by_id,
                library_revision=self._library_revision,
            )

    def get_app_setting(self, key: str) -> bool:
        with self._lock:
            return self._settings.get_bool(key)

    def set_app_setting(self, key: str, value: bool) -> None:
        with self._lock:
            self._settings.set_bool(key, value)

    def library_revision(self) -> int:
        with self._lock:
            return self._library_revision

    def has_pending_apply(self) -> bool:
        with self._lock:
            return self._has_pending_apply

    def set_has_pending_apply(self, value: bool) -> None:
        with self._lock:
            self._has_pending_apply = value

    def set_has_pending_quality_repair(self, value: bool) -> None:
        with self._lock:
            self._has_pending_quality_repair = value

    def has_pending_quality_repair(self) -> bool:
        with self._lock:
            return self._has_pending_quality_repair

    def repair_session_id(self) -> str:
        import hashlib

        with self._lock:
            folder = self._index.folder_path or ""
        return hashlib.sha256(folder.encode("utf-8")).hexdigest()[:16]

    def quality_issues(self) -> list[Any]:
        with self._lock:
            return list(self._index.quality_issues())

    def file_record_for_quality_issue(self, issue: Any) -> FileRecord | None:
        with self._lock:
            return self._files_by_id.get(issue.file_id)

    def reanalyze_quality_for_file_ids(self, file_ids: list[str]) -> None:
        with self._lock:
            folder = self._index.folder_path
            if not folder:
                return
            target_ids = set(file_ids)
            remaining = [
                issue for issue in self._index.quality_issues() if issue.file_id not in target_ids
            ]
            new_issues: list[Any] = []
            for file_id in file_ids:
                record = self._files_by_id.get(file_id)
                if record is None:
                    continue
                new_issues.extend(analyze_quality(folder, [record]))
            merged = remaining + new_issues
            self._index.replace_quality_issues(folder, merged)
            self._apply_quality_cache(merged)

    def first_file_id(self) -> str | None:
        with self._lock:
            files = self._index.files()
            return files[0].id if files else None

    def library_root_path(self) -> Path | None:
        with self._lock:
            folder = self._index.folder_path
            return Path(folder) if folder else None

    def review_rows_snapshot(self) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._review_rows_cache)

    def file_record_for_review_row(self, row: dict[str, Any]) -> FileRecord | None:
        from application.review_state_merge import _file_id_from_row_id

        with self._lock:
            row_id = str(row.get("id", ""))
            file_id = _file_id_from_row_id(row_id)
            if file_id:
                found = self._files_by_id.get(file_id)
                if found is not None:
                    return found
            path = row.get("path")
            if isinstance(path, str):
                for record in self._files_by_id.values():
                    if record.relative_path == path:
                        return record
            return None

    def increment_library_revision(self) -> None:
        with self._lock:
            self._library_revision += 1

    def update_review_decisions(
        self,
        selection: dict[str, Any],
        command: str,
        *,
        keeper_file_id: str | None = None,
    ) -> dict[str, Any]:
        from application.review_decisions import UpdateReviewDecisionsUseCase

        with self._lock:
            use_case = UpdateReviewDecisionsUseCase(self, self._index)
            updated = use_case.execute(
                selection,
                command,
                keeper_file_id=keeper_file_id,
            )
            if updated > 0:
                self._rebuild_review_index(list(self._files_by_id.values()))
                folder = self._index.folder_path
                if folder:
                    try:
                        self._run_post_scan_detection_phases(
                            folder, list(self._files_by_id.values())
                        )
                    except Exception:
                        _LOGGER.exception("post-scan detection failed after review update")
                self._library_revision += 1
            return {
                "updatedCount": updated,
                "libraryRevision": self._library_revision,
            }

    def set_apply_in_progress(self, value: bool) -> None:
        with self._lock:
            self._apply_in_progress = value

    def is_apply_or_scan_busy(self) -> bool:
        with self._lock:
            return self._apply_in_progress or self._pipeline_running

    def configure_finalize(self, runner: Any) -> None:
        with self._lock:
            self._finalize_runner = runner

    def scan_state(self) -> str:
        with self._lock:
            return self._scan_state

    def queue_count(self) -> int:
        with self._lock:
            return self._queue_count

    def conflict_count(self) -> int:
        with self._lock:
            return self._conflict_count

    def approved_count(self) -> int:
        with self._lock:
            return self._approved_count

    def encoding_issue_count(self) -> int:
        with self._lock:
            return self._encoding_issue_count

    def integrity_issue_count(self) -> int:
        with self._lock:
            return self._integrity_issue_count

    def small_file_anomaly_count(self) -> int:
        with self._lock:
            return self._small_file_anomaly_count

    def refresh_resolve_counts(self) -> None:
        with self._lock:
            self._refresh_resolve_counts()

    def finalize_session_id(self) -> str:
        return self.repair_session_id()

    def set_finalize_counts(self, blocker_count: int, warning_count: int) -> None:
        with self._lock:
            self._finalize_blocker_count = blocker_count
            self._finalize_warning_count = warning_count

    def set_finalize_last_run(
        self,
        *,
        report_id: str | None,
        last_status: str,
        report_path: str | None,
    ) -> None:
        with self._lock:
            self._finalize_last_report_id = report_id
            self._finalize_last_status = last_status
            self._finalize_last_report_path = report_path
            if last_status != "running":
                self._finalize_last_run_at = scan_timestamp()

    def get_finalize_summary(self, audit_log_path: Path) -> dict[str, Any]:
        from application.finalize_summary import build_finalize_summary

        with self._lock:
            return build_finalize_summary(
                library_revision=self._library_revision,
                scan_state=self._scan_state,
                review_rows=list(self._review_rows_cache),
                queue_count=self._queue_count,
                conflict_count=self._conflict_count,
                approved_count=self._approved_count,
                has_pending_apply=self._has_pending_apply,
                has_pending_quality_repair=self._has_pending_quality_repair,
                encoding_issue_count=self._encoding_issue_count,
                integrity_issue_count=self._integrity_issue_count,
                small_file_anomaly_count=self._small_file_anomaly_count,
                audit_log_path=audit_log_path,
            )

    def run_finalize_verification(self, request: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            if not self._index.folder_path:
                raise RuntimeError("NO_LIBRARY")
            if self._apply_in_progress or self._pipeline_running:
                raise RuntimeError("LIBRARY_BUSY")
            if self._finalize_runner is None:
                raise RuntimeError("FINALIZE_NOT_CONFIGURED")
            runner = self._finalize_runner
            include_cleanup = bool(request.get("includeCleanup"))
            self._cancel_requested = False
            self._pipeline_running = True
            self._pipeline_phase = "finalize"
            self._pipeline_percent = 0
            self._pipeline_label = "사전 조건 확인"
            self._pipeline_cancellable = True
            self._finalize_last_status = "running"

        result: dict[str, Any] = {}
        error: str | None = None

        def _run() -> None:
            nonlocal result, error
            try:

                def on_step(step: str, pct: int, label: str) -> None:
                    with self._lock:
                        self._pipeline_percent = pct
                        self._pipeline_label = label

                def cancel_check() -> bool:
                    with self._lock:
                        return self._cancel_requested

                result = runner.run(
                    self,
                    include_cleanup=include_cleanup,
                    cancel_check=cancel_check,
                    on_step=on_step,
                )
            except Exception as exc:
                error = str(exc)

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()
        thread.join()

        with self._lock:
            self._pipeline_running = False
            self._pipeline_cancellable = False
            self._pipeline_phase = "idle"
            self._pipeline_percent = 0
            self._pipeline_label = "대기 중"
            if error is not None:
                self._finalize_last_status = "error"
                return {
                    "status": "error",
                    "reportId": None,
                    "reportPath": None,
                    "libraryRevision": self._library_revision,
                    "blockers": [],
                    "warnings": [],
                    "cleanup": {"previewedEmptyDirs": [], "removedEmptyDirs": []},
                    "errorMessage": error,
                }
            return result

    def cancel_finalize(self) -> None:
        with self._lock:
            if self._pipeline_phase == "finalize" and self._pipeline_running:
                self._cancel_requested = True

    def read_finalize_report(self, save_root: Path, report_id: str) -> dict[str, Any]:
        from application.finalize_report import read_finalize_report

        return read_finalize_report(save_root, self.finalize_session_id(), report_id)

    def refresh_index_from_disk(self) -> None:
        with self._lock:
            folder = self._index.folder_path
            if not folder:
                return
        collected: list[FileRecord] = []

        def on_progress(_pct: int, _label: str) -> None:
            return

        def cancel_check() -> bool:
            return False

        self._scan_folder(
            folder,
            on_progress=on_progress,
            cancel_check=cancel_check,
            out=collected.append,
        )
        with self._lock:
            self._index.replace_files(folder, collected)
            self._rebuild_review_index(collected)
            self._rebuild_quality_index(folder, collected)
            try:
                self._run_post_scan_detection_phases(folder, collected)
            except Exception:
                _LOGGER.exception("post-scan detection failed")

    def _clear_review_cache(self) -> None:
        self._review_rows_cache = []
        self._near_groups_by_id = {}
        self._relation_groups_by_id = {}
        self._duplicate_group_count = 0
        self._queue_count = 0
        self._approved_count = 0
        self._conflict_count = 0
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
        folder = self._index.folder_path
        if folder:
            valid_group_ids = {g.group_id for g in groups}
            valid_file_ids = {f.id for f in files}
            self._index.prune_review_state(folder, valid_group_ids, valid_file_ids)
            stored = self._index.load_review_state(folder)
            self._review_rows_cache = rebuild_rows_with_review_state(files, stored)
        else:
            self._review_rows_cache = build_review_rows(groups, self._files_by_id)
        self._duplicate_group_count = len(groups)
        self._refresh_resolve_counts()

    def _refresh_resolve_counts(self) -> None:
        queue, approved, conflict = file_row_status_counts(self._review_rows_cache)
        self._queue_count = queue
        self._approved_count = approved
        self._conflict_count = conflict

    def _strip_near_rows(self) -> None:
        self._review_rows_cache = [
            row for row in self._review_rows_cache if row.get("type") != "near"
        ]

    def _strip_relation_rows(self) -> None:
        self._review_rows_cache = [
            row for row in self._review_rows_cache if row.get("type") != "relation"
        ]

    def _run_post_scan_detection_phases(self, folder: str, files: list[FileRecord]) -> None:
        self._run_near_duplicate_phase(folder, files)
        self._run_relation_phase(folder, files)

    def _run_relation_phase(self, folder: str, files: list[FileRecord]) -> None:
        from application.relation_batch_id import filename_set_digest, make_relation_batch_id
        from application.relation_membership import (
            build_exact_membership_by_file_id,
            build_near_membership_by_file_id,
        )
        from application.relation_review_rows_builder import build_relation_review_rows
        from application.review_state_merge import merge_review_state
        from domain.duplicate_exact import find_exact_duplicate_groups
        from domain.filename_relation import detect_filename_relations

        self._strip_relation_rows()
        self._relation_groups_by_id = {}

        if not self._settings.get_bool(SETTINGS_KEY_INCLUDE_RELATION):
            return

        relation_batch_id = make_relation_batch_id(
            library_revision=self._library_revision,
            filename_set_digest_value=filename_set_digest(files),
        )
        result = detect_filename_relations(
            files,
            exact_membership_by_file_id=build_exact_membership_by_file_id(files),
            near_membership_by_file_id=build_near_membership_by_file_id(self._near_groups_by_id),
            relation_batch_id=relation_batch_id,
        )
        self._relation_groups_by_id = {group.group_id: group for group in result.groups}

        relation_skeleton = build_relation_review_rows(list(result.groups), self._files_by_id)
        stored = self._index.load_review_state(folder)
        exact_groups = find_exact_duplicate_groups(files)
        relation_rows = merge_review_state(
            relation_skeleton,
            stored,
            groups=exact_groups,
            files_by_id=self._files_by_id,
        )
        self._review_rows_cache.extend(relation_rows)

        valid_group_ids = (
            {group.group_id for group in exact_groups}
            | set(self._near_groups_by_id.keys())
            | set(self._relation_groups_by_id.keys())
        )
        valid_file_ids = {file_record.id for file_record in files}
        self._index.prune_review_state(folder, valid_group_ids, valid_file_ids)
        self._refresh_resolve_counts()

    def _run_near_duplicate_phase(self, folder: str, files: list[FileRecord]) -> None:
        from application.near_batch_id import content_set_digest, make_near_batch_id
        from application.near_duplicate_detect import (
            build_exact_group_by_file_id,
            run_near_duplicate_detection,
        )
        from application.near_review_rows_builder import build_near_review_rows
        from application.review_state_merge import merge_review_state
        from domain.duplicate_exact import find_exact_duplicate_groups

        root = Path(folder)
        self._strip_near_rows()
        self._near_groups_by_id = {}

        near_batch_id = make_near_batch_id(
            library_revision=self._library_revision,
            folder_path=folder,
            content_set_digest_value=content_set_digest(files),
            scan_completed_at=self._scan_last_run,
        )
        exact_group_by_file_id = build_exact_group_by_file_id(files)
        result = run_near_duplicate_detection(
            root=root,
            files=files,
            near_batch_id=near_batch_id,
            exact_group_by_file_id=exact_group_by_file_id,
        )
        self._index.replace_near_duplicate_results(folder, result)
        self._near_groups_by_id = {group.group_id: group for group in result.groups}

        near_skeleton = build_near_review_rows(list(result.groups), self._files_by_id)
        stored = self._index.load_review_state(folder)
        exact_groups = find_exact_duplicate_groups(files)
        near_rows = merge_review_state(
            near_skeleton,
            stored,
            groups=exact_groups,
            files_by_id=self._files_by_id,
        )
        self._review_rows_cache.extend(near_rows)

        valid_group_ids = {group.group_id for group in exact_groups} | set(
            self._near_groups_by_id.keys()
        )
        valid_file_ids = {file_record.id for file_record in files}
        self._index.prune_review_state(folder, valid_group_ids, valid_file_ids)
        self._refresh_resolve_counts()

    def _rebuild_quality_index(self, folder: str, files: list[FileRecord]) -> None:
        issues = analyze_quality(folder, files)
        self._index.replace_quality_issues(folder, issues)
        self._apply_quality_cache(issues)

    def _apply_quality_cache(self, issues: list[Any]) -> None:
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
            try:
                self._run_post_scan_detection_phases(folder, collected)
            except Exception:
                _LOGGER.exception("post-scan detection failed")
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
