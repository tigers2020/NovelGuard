"""Library orchestration for pywebview bridge (PR-14a/14b)."""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from application import scan_pipeline_constants
from application.app_settings import AppSettings, InvalidSettingValueError
from application.bridge_timing import log_phase_end, log_phase_start
from application.dto_mapper import (
    build_snapshot,
    scan_timestamp,
)
from application.file_row_query import normalize_file_rows_query
from application.library_folder_persistence import (
    is_persistable_library_folder,
    normalize_library_folder_path,
)
from application.log_buffer import query_log_entries
from application.logs_artifacts import list_logs_artifacts
from application.ports.library_index import LibraryIndexPort
from application.quality_analyzer import analyze_quality
from application.quality_issue_detail import build_quality_issue_detail
from application.quality_query import query_quality_page
from application.quality_rows_builder import build_quality_rows
from application.review_auto_approve import persist_exact_non_keeper_approvals
from application.review_query import query_review_page
from application.review_rows_builder import build_review_rows
from application.review_snapshot_counts import file_row_status_counts, resolve_insight_counts
from application.review_state_merge import rebuild_rows_with_review_state
from application.scan_settings import build_scan_options_labels, parse_extension_filter
from domain.duplicate_exact import find_exact_duplicate_groups
from domain.duplicate_near import NearDuplicateGroup
from domain.filename_relation import RelationGroup
from domain.models import FileRecord
from domain.settings_keys import (
    SETTINGS_KEY_INCLUDE_RELATION,
    SETTINGS_KEY_LIBRARY_LAST_FOLDER_PATH,
    SETTINGS_KEY_SCAN_EXTENSION_FILTER,
    SETTINGS_KEY_SCAN_INCLUDE_HIDDEN,
)

_MAX_QUERY_LIMIT = 200
_DEFAULT_QUERY_LIMIT = 100
_WORK_MODES = frozenset({"scan", "resolve", "quality"})
_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class _RelationPhaseInputs:
    folder: str
    files: tuple[FileRecord, ...]
    files_by_id: dict[str, FileRecord]
    near_groups_by_id: dict[str, NearDuplicateGroup]
    library_revision: int
    include_relation: bool


@dataclass(frozen=True)
class _RelationPhaseResult:
    relation_groups_by_id: dict[str, RelationGroup]
    relation_rows: list[dict[str, Any]]
    valid_group_ids: set[str]
    valid_file_ids: set[str]


@dataclass(frozen=True)
class _NearPhaseInputs:
    folder: str
    files: tuple[FileRecord, ...]
    files_by_id: dict[str, FileRecord]
    library_revision: int
    scan_last_run: str | None


@dataclass(frozen=True)
class _NearPhaseComputeResult:
    detection_result: Any
    near_rows: list[dict[str, Any]]
    near_groups_by_id: dict[str, NearDuplicateGroup]
    valid_group_ids: set[str]
    valid_file_ids: set[str]


def _record_for_quality_recheck(record: FileRecord) -> FileRecord:
    return FileRecord(
        id=record.id,
        relative_path=record.relative_path,
        name=record.name,
        size_bytes=record.size_bytes,
        modified_at_ns=record.modified_at_ns,
        extension=record.extension,
        content_sha256=record.content_sha256,
        encoding_status=None,
        near_text_preview=None,
    )


def _normalize_active_mode(mode: str) -> str:
    if mode == "finalize":
        return "resolve"
    if mode in _WORK_MODES:
        return mode
    return "resolve"


class LibrarySession:
    def __init__(
        self,
        index: LibraryIndexPort,
        *,
        scan_folder: Callable[..., Any],
        on_library_selected: Callable[["LibrarySession", str], Any] | None = None,
        settings: AppSettings | None = None,
    ) -> None:
        self._lock = threading.RLock()
        self._index = index
        self._scan_folder = scan_folder
        self._on_library_selected = on_library_selected
        self._runtime_paths: Any | None = None
        self._library_revision = 0
        self._active_mode = "resolve"
        self._pipeline_running = False
        self._pipeline_phase = "idle"
        self._pipeline_percent = 0
        self._pipeline_label = "대기 중"
        self._pipeline_cancellable = False
        self._scan_state = "empty"
        self._exact_auto_approved_count = 0
        self._scan_last_run: str | None = None
        self._index_ready = False
        self._deep_analysis_complete = False
        self._deep_analysis_status: Literal["idle", "running", "complete", "error"] = "idle"
        self._deep_analysis_error: str | None = None
        self._cancel_requested = False
        self._scan_thread: threading.Thread | None = None
        self._post_scan_running = False
        self._background_active = False
        self._background_phase = "idle"
        self._background_label = ""
        self._background_step = 0
        self._background_step_total = 0
        self._background_percent = 0
        self._index_save_total: int | None = None
        self._index_save_committed: int | None = None
        self._index_save_total_bytes: int | None = None
        self._backup_files: list[FileRecord] | None = None
        self._backup_folder: str | None = None
        self._has_pending_apply = False
        self._deferred_revision_bumps = 0
        self._review_rows_cache: list[dict[str, Any]] = []
        self._duplicate_group_count = 0
        self._queue_count = 0
        self._move_ready_count = 0
        self._review_signal_count = 0
        self._approved_count = 0
        self._conflict_count = 0
        self._exact_auto_approved_count = 0
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
        from application.resolve_auto_approve_job import idle_resolve_auto_approve_job_snapshot

        self._resolve_auto_approve_job = idle_resolve_auto_approve_job_snapshot()
        self._resolve_auto_approve_running = False
        self._resolve_auto_approve_cancel_requested = False
        self._resolve_auto_approve_thread: threading.Thread | None = None
        from application.finalize_job import idle_finalize_job_snapshot

        self._finalize_job = idle_finalize_job_snapshot()
        self._finalize_running = False
        self._finalize_cancel_requested = False
        self._finalize_thread: threading.Thread | None = None
        self._settings = settings or AppSettings()

    @property
    def index(self) -> LibraryIndexPort:
        return self._index

    def apply_library_runtime(
        self,
        paths: Any,
        *,
        rebind_sqlite: bool,
    ) -> None:
        with self._lock:
            if rebind_sqlite:
                from infrastructure.sqlite_library_index import SqliteLibraryIndex

                self._index = SqliteLibraryIndex(paths.db_path)
            self._runtime_paths = paths
            from application.finalize_runner import FinalizeRunner
            from infrastructure.finalize_cleanup import LocalFinalizeCleanupAdapter

            self._finalize_runner = FinalizeRunner(
                cleanup=LocalFinalizeCleanupAdapter(),
                save_root=paths.finalize_save_root,
                audit_log_path=paths.audit_log_path,
            )

    def audit_log_path(self) -> Path:
        with self._lock:
            if self._runtime_paths is None:
                raise RuntimeError("Library runtime paths not configured")
            path: Path = self._runtime_paths.audit_log_path
            return path

    def finalize_save_root(self) -> Path:
        with self._lock:
            if self._runtime_paths is None:
                raise RuntimeError("Library runtime paths not configured")
            path: Path = self._runtime_paths.finalize_save_root
            return path

    def repair_backup_root(self) -> Path:
        with self._lock:
            if self._runtime_paths is None:
                raise RuntimeError("Library runtime paths not configured")
            path: Path = self._runtime_paths.repair_backup_root
            return path

    def select_folder(self, path: str | None = None) -> None:
        remember_folder = path is None
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
            title = "스캔 폴더 선택"
            last_folder = self._saved_library_folder_path()
            try:
                if last_folder is not None:
                    picked = filedialog.askdirectory(title=title, initialdir=last_folder)
                else:
                    picked = filedialog.askdirectory(title=title)
            finally:
                root.destroy()
            if not picked:
                return
            folder = picked

        folder = normalize_library_folder_path(folder)
        if not Path(folder).is_dir():
            raise ValueError(f"Not a directory: {folder}")

        if self._on_library_selected is not None:
            self._on_library_selected(self, folder)

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
            if remember_folder:
                self._persist_last_library_folder(folder)

    def restore_last_library_folder(self) -> bool:
        folder = self._saved_library_folder_path()
        if folder is None:
            return False

        if self._on_library_selected is not None:
            self._on_library_selected(self, folder)

        with self._lock:
            self._index.activate_library_folder(folder)
            files = self._index.files()
            self._backup_files = None
            self._backup_folder = None
            self._pipeline_phase = "idle"
            self._pipeline_percent = 0
            self._pipeline_label = "대기 중"
            self._pipeline_cancellable = False
            if not files:
                self._clear_review_cache()
                self._scan_state = "ready"
                self._scan_last_run = None
                return True
            self._hydrate_from_persisted_index(folder, files)
        return True

    def _saved_library_folder_path(self) -> str | None:
        raw, _ = self._settings.get_value(SETTINGS_KEY_LIBRARY_LAST_FOLDER_PATH)
        if not isinstance(raw, str) or not raw.strip():
            return None
        folder = normalize_library_folder_path(raw)
        if not Path(folder).is_dir():
            self._clear_persisted_library_folder()
            return None
        if not is_persistable_library_folder(folder):
            self._clear_persisted_library_folder()
            return None
        return folder

    def _persist_last_library_folder(self, folder: str) -> None:
        if not is_persistable_library_folder(folder):
            return
        self._settings.set_value(
            SETTINGS_KEY_LIBRARY_LAST_FOLDER_PATH,
            normalize_library_folder_path(folder),
        )

    def _clear_persisted_library_folder(self) -> None:
        self._settings.set_value(SETTINGS_KEY_LIBRARY_LAST_FOLDER_PATH, "")

    def _hydrate_from_persisted_index(self, folder: str, files: list[FileRecord]) -> None:
        self._rebuild_review_index(files)
        self._apply_quality_cache(list(self._index.quality_issues()))
        self._restore_near_cache(folder, files)
        if self._settings.get_bool(SETTINGS_KEY_INCLUDE_RELATION):
            try:
                self._run_relation_phase(folder, files)
            except Exception:
                _LOGGER.exception("relation restore failed")
        self._scan_state = "success"
        self._scan_last_run = None
        self._index_ready = bool(files)
        self._deep_analysis_complete = True
        self._deep_analysis_status = "complete"
        self._deep_analysis_error = None

    def start_scan(self, options: dict[str, Any] | None = None) -> None:
        _ = options
        with self._lock:
            folder = self._index.folder_path
            if not folder or self._pipeline_running or self._apply_in_progress:
                return
            self._exact_auto_approved_count = 0
            self._backup_files = self._index.files()
            self._backup_folder = folder
            self._cancel_requested = False
            self._index_ready = False
            self._deep_analysis_complete = False
            self._deep_analysis_status = "idle"
            self._deep_analysis_error = None
            self._pipeline_running = True
            self._pipeline_phase = "probe"
            self._pipeline_percent = 0
            self._pipeline_label = "파일 확인 중…"
            self._pipeline_cancellable = True
            self._scan_state = "running"
            self._exact_auto_approved_count = 0
            self._scan_thread = threading.Thread(target=self._run_scan, args=(folder,), daemon=True)
            self._scan_thread.start()

    def cancel_run(self) -> None:
        with self._lock:
            if not self._pipeline_running:
                return
            self._cancel_requested = True

    def set_work_mode(self, mode: str) -> None:
        if mode not in _WORK_MODES:
            raise ValueError(f"INVALID_WORK_MODE:{mode}")
        with self._lock:
            self._active_mode = mode

    def _scan_options_labels(self) -> list[str]:
        extension_filter, _ = self._settings.get_value(SETTINGS_KEY_SCAN_EXTENSION_FILTER)
        include_hidden = self._settings.get_bool(SETTINGS_KEY_SCAN_INCLUDE_HIDDEN)
        return build_scan_options_labels(
            extension_filter=str(extension_filter),
            include_hidden=include_hidden,
        )

    def _snapshot_library_metrics(self) -> tuple[int, int]:
        return self._index.file_count(), self._index.total_bytes()

    def get_snapshot(self) -> dict[str, Any]:
        with self._lock:
            file_count, total_bytes = self._snapshot_library_metrics()
            return build_snapshot(
                folder_path=self._index.folder_path,
                file_count=file_count,
                total_bytes=total_bytes,
                library_revision=self._library_revision,
                active_mode=_normalize_active_mode(self._active_mode),
                pipeline_phase=self._pipeline_phase,
                pipeline_percent=self._pipeline_percent,
                pipeline_label=self._pipeline_label,
                pipeline_cancellable=self._pipeline_cancellable,
                pipeline_background=self._pipeline_background_payload(),
                scan_state=self._scan_state,
                scan_last_run=self._scan_last_run,
                exact_auto_approved_count=self._exact_auto_approved_count,
                index_ready=self._index_ready,
                deep_analysis_complete=self._deep_analysis_complete,
                deep_analysis_status=self._deep_analysis_status,
                deep_analysis_error=self._deep_analysis_error,
                has_pending_apply=self._has_pending_apply,
                duplicate_group_count=self._duplicate_group_count,
                queue_count=self._queue_count,
                move_ready_count=self._move_ready_count,
                review_signal_count=self._review_signal_count,
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
                scan_options=self._scan_options_labels(),
                resolve_auto_approve_job=self._resolve_auto_approve_job,
                finalize_job=self._finalize_job,
            )

    def query_review_rows(self, query: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            limit = _clamp_query_limit(query)
            return query_review_page(self._review_rows_cache, query, limit=limit)

    def query_quality_rows(self, query: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            limit = _clamp_query_limit(query)
            return query_quality_page(self._quality_rows_cache, query, limit=limit)

    def query_file_rows(self, query: dict[str, Any]) -> dict[str, Any]:
        # File row pages read SQLite directly; do not block on long post-scan analysis locks.
        normalized = normalize_file_rows_query(query)
        return self._index.query_file_rows_page(normalized)

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

    def get_app_setting(self, key: str) -> dict[str, Any]:
        with self._lock:
            value, source = self._settings.get_value(key)
            return {"key": key, "value": value, "source": source}

    def set_app_setting(self, key: str, value: Any) -> dict[str, Any]:
        with self._lock:
            if key == SETTINGS_KEY_SCAN_EXTENSION_FILTER:
                if not isinstance(value, str):
                    raise InvalidSettingValueError("scan.extensionFilter requires str")
                parse_extension_filter(value)
            stored, source = self._settings.set_value(key, value)
            return {"key": key, "value": stored, "source": source}

    def query_log_entries(self, query: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            return query_log_entries(query)

    def get_logs_artifacts(self, *, packaging_log_path: Path | None = None) -> dict[str, Any]:
        with self._lock:
            audit_path: Path | None = None
            finalize_root: Path | None = None
            if self._runtime_paths is not None:
                audit_path = self._runtime_paths.audit_log_path
                finalize_root = self._runtime_paths.finalize_save_root
            if self._index.folder_path is None:
                return {"artifacts": []}
            return list_logs_artifacts(
                audit_log_path=audit_path,
                finalize_save_root=finalize_root,
                finalize_session_id=self.finalize_session_id(),
                packaging_log_path=packaging_log_path,
            )

    def near_groups_by_id(self) -> dict[str, NearDuplicateGroup]:
        with self._lock:
            return dict(self._near_groups_by_id)

    def relation_groups_by_id(self) -> dict[str, RelationGroup]:
        with self._lock:
            return dict(self._relation_groups_by_id)

    def summarize_auto_select_keepers(self, query: dict[str, Any]) -> dict[str, Any]:
        from application.auto_select_summary import summarize_auto_select_keepers as summarize

        with self._lock:
            return summarize(
                self._review_rows_cache,
                query,
                files_by_id=self._files_by_id,
            )

    def summarize_resolve_auto_approve(self, query: dict[str, Any]) -> dict[str, Any]:
        from application.summarize_resolve_auto_approve import summarize_resolve_auto_approve

        with self._lock:
            return summarize_resolve_auto_approve(
                self._review_rows_cache,
                query,
                files_by_id=self._files_by_id,
                members_by_group=self.build_review_members_by_group(),
            )

    def resolve_auto_approve_job_snapshot(self) -> dict[str, Any]:
        with self._lock:
            return dict(self._resolve_auto_approve_job)

    def is_resolve_auto_approve_job_running(self) -> bool:
        with self._lock:
            return self._resolve_auto_approve_running

    def start_resolve_auto_approve_job(self, query: dict[str, Any]) -> dict[str, Any]:
        from app.bridge_contract import ResolveAutoApproveJobError
        from application.resolve_auto_approve_job import (
            _iso_now,
            build_resolve_auto_approve_job_snapshot,
        )
        from application.summarize_resolve_auto_approve import has_unreviewed_resolve_targets

        with self._lock:
            if self._resolve_auto_approve_running:
                raise ResolveAutoApproveJobError("JOB_ALREADY_RUNNING")
            if not has_unreviewed_resolve_targets(self._review_rows_cache, query):
                raise ResolveAutoApproveJobError("NO_UNREVIEWED_TARGETS")

            started_at = _iso_now()
            self._resolve_auto_approve_running = True
            self._resolve_auto_approve_cancel_requested = False
            self._resolve_auto_approve_job = build_resolve_auto_approve_job_snapshot(
                status="running",
                phase="summarize",
                label="미검토 대상 집계 중…",
                started_at=started_at,
            )
            captured_query = dict(query)

        self._append_resolve_auto_approve_audit("resolve_auto_approve_job_started")
        self._start_resolve_auto_approve_worker(captured_query)
        return {"accepted": True}

    def cancel_resolve_auto_approve_job(self) -> None:
        with self._lock:
            if not self._resolve_auto_approve_running:
                return
            self._resolve_auto_approve_cancel_requested = True

    def _append_resolve_auto_approve_audit(self, event: str, **fields: Any) -> None:
        try:
            from application.audit_log import AuditLog

            AuditLog(self.audit_log_path()).append(event, **fields)
        except RuntimeError:
            pass

    def _start_resolve_auto_approve_worker(self, query: dict[str, Any]) -> None:
        def _worker() -> None:
            from application.resolve_auto_approve_job import (
                ResolveAutoApproveJobCancelled,
                _iso_now,
                build_resolve_auto_approve_job_snapshot,
                run_resolve_auto_approve_job,
            )

            final_status = "complete"
            error_message: str | None = None
            job_result: Any = None

            class _JobMutator:
                def apply_review_decisions(
                    self,
                    selection: dict[str, Any],
                    command: str,
                    *,
                    keeper_file_id: str | None = None,
                ) -> int:
                    return LibrarySession.apply_review_decisions_for_auto_approve_job(
                        self_outer,
                        selection,
                        command,
                        keeper_file_id=keeper_file_id,
                    )

                def finalize_projection(self) -> None:
                    self_outer.finalize_auto_approve_job_projection()

                def library_revision(self) -> int:
                    return self_outer.library_revision()

            self_outer = self

            def _cancel_check() -> bool:
                with self._lock:
                    return self._resolve_auto_approve_cancel_requested

            def _on_progress(counts: dict[str, Any]) -> None:
                with self._lock:
                    if not self._resolve_auto_approve_running:
                        return
                    current = dict(self._resolve_auto_approve_job)
                    for key, value in counts.items():
                        if key == "phase":
                            current["phase"] = value
                        elif key == "label":
                            current["label"] = value
                        elif key == "persistedRevision":
                            current["persistedRevision"] = value
                        elif key in current:
                            current[key] = value
                    self._resolve_auto_approve_job = current

            try:
                with self._lock:
                    rows = list(self._review_rows_cache)
                    files_by_id = dict(self._files_by_id)
                    members_by_group = self.build_review_members_by_group()

                job_result = run_resolve_auto_approve_job(
                    rows,
                    query,
                    files_by_id=files_by_id,
                    members_by_group=members_by_group,
                    mutator=_JobMutator(),
                    on_progress=_on_progress,
                    cancel_check=_cancel_check,
                )
            except ResolveAutoApproveJobCancelled:
                final_status = "cancelled"
            except Exception as exc:
                _LOGGER.exception("resolve auto-approve job failed")
                final_status = "error"
                error_message = str(exc)
            else:
                if _cancel_check():
                    final_status = "cancelled"

            finished_at = _iso_now()
            with self._lock:
                started_at = self._resolve_auto_approve_job.get("startedAt")
                current = dict(self._resolve_auto_approve_job)
                if final_status == "complete" and job_result is not None:
                    summary = job_result.summary
                    self._resolve_auto_approve_job = build_resolve_auto_approve_job_snapshot(
                        status="complete",
                        phase="idle",
                        processed_rows=int(summary["unreviewedCount"]),
                        total_rows=int(summary["unreviewedCount"]),
                        keeper_count=int(summary["keeperCount"]),
                        move_candidate_count=int(summary["moveCandidateCount"]),
                        scanned_count=int(summary["unreviewedCount"]),
                        eligible_count=int(summary["unreviewedCount"]),
                        skipped_conflict_count=int(summary["skippedConflictCount"]),
                        skipped_excluded_count=int(summary["skippedExcludedCount"]),
                        keeper_set_count=job_result.keeper_set_count,
                        approved_row_count=job_result.approved_row_count,
                        mutation_count=job_result.mutation_count,
                        persisted_revision=job_result.persisted_revision,
                        label="처리 완료",
                        started_at=started_at if isinstance(started_at, str) else None,
                        finished_at=finished_at,
                        summary=summary,
                    )
                elif final_status == "cancelled":
                    self._resolve_auto_approve_job = build_resolve_auto_approve_job_snapshot(
                        status="cancelled",
                        phase="idle",
                        processed_rows=current.get("processedRows", 0),
                        total_rows=current.get("totalRows", 0),
                        keeper_count=current.get("keeperCount", 0),
                        move_candidate_count=current.get("moveCandidateCount", 0),
                        scanned_count=current.get("scannedCount", 0),
                        eligible_count=current.get("eligibleCount", 0),
                        skipped_conflict_count=current.get("skippedConflictCount", 0),
                        skipped_excluded_count=current.get("skippedExcludedCount", 0),
                        keeper_set_count=current.get("keeperSetCount", 0),
                        approved_row_count=current.get("approvedRowCount", 0),
                        mutation_count=current.get("mutationCount", 0),
                        persisted_revision=current.get("persistedRevision"),
                        label="취소됨",
                        error=None,
                        started_at=started_at if isinstance(started_at, str) else None,
                        finished_at=finished_at,
                        summary=current.get("summary"),
                    )
                else:
                    self._resolve_auto_approve_job = build_resolve_auto_approve_job_snapshot(
                        status="error",
                        phase="idle",
                        processed_rows=current.get("processedRows", 0),
                        total_rows=current.get("totalRows", 0),
                        keeper_set_count=current.get("keeperSetCount", 0),
                        approved_row_count=current.get("approvedRowCount", 0),
                        mutation_count=current.get("mutationCount", 0),
                        persisted_revision=current.get("persistedRevision"),
                        label="처리 실패",
                        error=error_message or "unknown error",
                        started_at=started_at if isinstance(started_at, str) else None,
                        finished_at=finished_at,
                        summary=current.get("summary"),
                    )
                self._resolve_auto_approve_running = False
                self._resolve_auto_approve_cancel_requested = False
                self._resolve_auto_approve_thread = None

            if final_status == "complete":
                self._append_resolve_auto_approve_audit(
                    "resolve_auto_approve_job_completed",
                    mutationCount=job_result.mutation_count if job_result else 0,
                )
            elif final_status == "cancelled":
                self._append_resolve_auto_approve_audit("resolve_auto_approve_job_cancelled")
            else:
                self._append_resolve_auto_approve_audit(
                    "resolve_auto_approve_job_error",
                    error=error_message,
                )

        thread = threading.Thread(
            target=_worker,
            name="novelguard-resolve-auto-approve",
            daemon=True,
        )
        with self._lock:
            self._resolve_auto_approve_thread = thread
        thread.start()

    def library_revision(self) -> int:
        with self._lock:
            return self._library_revision

    def has_pending_apply(self) -> bool:
        with self._lock:
            return self._has_pending_apply

    def set_has_pending_apply(self, value: bool) -> None:
        with self._lock:
            was_pending = self._has_pending_apply
            self._has_pending_apply = value
            if was_pending and not value:
                self._flush_deferred_revision_bumps_locked()

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
                new_issues.extend(analyze_quality(folder, [_record_for_quality_recheck(record)]))
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

    def reconcile_members_already_at_move_target(self, file_ids: list[str]) -> int:
        """Persist excluded status for duplicate members already under the move target folder."""
        with self._lock:
            folder = self._index.folder_path
            if not folder or not file_ids:
                return 0
            updated = 0
            for file_id in file_ids:
                if file_id not in self._files_by_id:
                    continue
                self._index.upsert_review_member(folder, file_id, "excluded")
                updated += 1
            if updated:
                self._rebuild_review_index(list(self._files_by_id.values()))
                self._library_revision += 1
            return updated

    def increment_library_revision(self) -> None:
        with self._lock:
            self._library_revision += 1

    def bump_library_revision_unless_pending_apply(self) -> None:
        """Defer revision bumps while a move preview is pending (background analysis safe)."""
        with self._lock:
            if self._has_pending_apply:
                self._deferred_revision_bumps += 1
                return
            self._library_revision += 1

    def _flush_deferred_revision_bumps_locked(self) -> None:
        if self._deferred_revision_bumps:
            self._library_revision += self._deferred_revision_bumps
            self._deferred_revision_bumps = 0

    def build_review_members_by_group(self) -> dict[str, set[str]]:
        from domain.duplicate_exact import find_exact_duplicate_groups

        files = list(self._files_by_id.values())
        members: dict[str, set[str]] = {}
        for exact_group in find_exact_duplicate_groups(files):
            members[exact_group.group_id] = set(exact_group.member_ids)
        for near_group in self._near_groups_by_id.values():
            members[near_group.group_id] = set(near_group.member_file_ids)
        for relation_group in self._relation_groups_by_id.values():
            members[relation_group.group_id] = set(relation_group.member_file_ids)
        return members

    def update_review_decisions(
        self,
        selection: dict[str, Any],
        command: str,
        *,
        keeper_file_id: str | None = None,
    ) -> dict[str, Any]:
        with self._lock:
            updated = self._apply_review_decisions_locked(
                selection,
                command,
                keeper_file_id=keeper_file_id,
                refresh_cache=True,
                run_post_scan=True,
            )
            return {
                "updatedCount": updated,
                "libraryRevision": self._library_revision,
            }

    def _apply_review_decisions_locked(
        self,
        selection: dict[str, Any],
        command: str,
        *,
        keeper_file_id: str | None = None,
        refresh_cache: bool,
        run_post_scan: bool,
    ) -> int:
        from application.review_decisions import UpdateReviewDecisionsUseCase

        use_case = UpdateReviewDecisionsUseCase(self, self._index)
        updated = use_case.execute(
            selection,
            command,
            keeper_file_id=keeper_file_id,
        )
        if updated > 0:
            if refresh_cache:
                self._rebuild_review_index(
                    list(self._files_by_id.values()),
                    sync_projection=run_post_scan,
                )
            if run_post_scan:
                folder = self._index.folder_path
                if folder:
                    try:
                        self._run_post_scan_detection_phases(
                            folder, list(self._files_by_id.values())
                        )
                    except Exception:
                        _LOGGER.exception("post-scan detection failed after review update")
            self._library_revision += 1
        return updated

    def apply_review_decisions_for_auto_approve_job(
        self,
        selection: dict[str, Any],
        command: str,
        *,
        keeper_file_id: str | None = None,
    ) -> int:
        with self._lock:
            return self._apply_review_decisions_locked(
                selection,
                command,
                keeper_file_id=keeper_file_id,
                refresh_cache=False,
                run_post_scan=False,
            )

    def finalize_auto_approve_job_projection(self) -> None:
        with self._lock:
            if not self._files_by_id:
                return
            self._rebuild_review_index(
                list(self._files_by_id.values()),
                sync_projection=True,
            )

    def set_apply_in_progress(self, value: bool) -> None:
        with self._lock:
            self._apply_in_progress = value

    def is_apply_or_scan_busy(self) -> bool:
        with self._lock:
            return (
                self._apply_in_progress
                or self._pipeline_running
                or self._post_scan_running
                or self._resolve_auto_approve_running
            )

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

    def preview_finalize_cleanup(self) -> dict[str, Any]:
        from infrastructure.finalize_cleanup import LocalFinalizeCleanupAdapter

        with self._lock:
            if not self._index.folder_path:
                raise RuntimeError("NO_LIBRARY")
            if self._apply_in_progress or self._pipeline_running:
                raise RuntimeError("LIBRARY_BUSY")
            root = str(self._index.folder_path)
        previewed = LocalFinalizeCleanupAdapter().list_empty_dirs(root)
        return {"previewedEmptyDirs": previewed}

    def get_finalize_summary(self, audit_log_path: Path | None = None) -> dict[str, Any]:
        from application.finalize_summary import build_finalize_summary

        with self._lock:
            if audit_log_path is not None:
                resolved_audit = audit_log_path
            elif self._runtime_paths is not None:
                resolved_audit = self._runtime_paths.audit_log_path
            else:
                raise RuntimeError("Library runtime paths not configured")
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
                audit_log_path=resolved_audit,
            )

    def finalize_job_snapshot(self) -> dict[str, Any]:
        with self._lock:
            return dict(self._finalize_job)

    def is_finalize_job_running(self) -> bool:
        with self._lock:
            return self._finalize_running

    def start_finalize_job(self, request: dict[str, Any]) -> dict[str, Any]:
        from app.bridge_contract import FinalizeJobError
        from application.finalize_job import (
            _iso_now,
            build_finalize_job_snapshot,
            new_finalize_job_id,
        )

        with self._lock:
            if not self._index.folder_path:
                raise RuntimeError("NO_LIBRARY")
            if self._finalize_running:
                raise FinalizeJobError("JOB_ALREADY_RUNNING")
            if self._apply_in_progress or self._pipeline_running:
                raise RuntimeError("LIBRARY_BUSY")
            if self._finalize_runner is None:
                raise RuntimeError("FINALIZE_NOT_CONFIGURED")

            include_cleanup = bool(request.get("includeCleanup"))
            job_id = new_finalize_job_id()
            started_at = _iso_now()
            self._finalize_running = True
            self._finalize_cancel_requested = False
            self._cancel_requested = False
            self._pipeline_running = True
            self._pipeline_phase = "finalize"
            self._pipeline_percent = 0
            self._pipeline_label = "사전 조건 확인"
            self._pipeline_cancellable = True
            self._finalize_last_status = "running"
            self._finalize_job = build_finalize_job_snapshot(
                job_id=job_id,
                status="running",
                progress=0,
                message="사전 조건 확인",
                started_at=started_at,
            )
            captured_include_cleanup = include_cleanup
            runner = self._finalize_runner

        self._start_finalize_worker(captured_include_cleanup, runner)
        with self._lock:
            return dict(self._finalize_job)

    def _start_finalize_worker(self, include_cleanup: bool, runner: Any) -> None:
        def _worker() -> None:
            from application.finalize_job import _iso_now, build_finalize_job_snapshot

            final_status = "succeeded"
            error_message: str | None = None
            result: dict[str, Any] | None = None

            def on_step(_step: str, pct: int, label: str) -> None:
                with self._lock:
                    if not self._finalize_running:
                        return
                    self._pipeline_percent = pct
                    self._pipeline_label = label
                    current = dict(self._finalize_job)
                    current["progress"] = pct
                    current["message"] = label
                    self._finalize_job = current

            def cancel_check() -> bool:
                with self._lock:
                    return self._finalize_cancel_requested or self._cancel_requested

            try:
                result = runner.run(
                    self,
                    include_cleanup=include_cleanup,
                    cancel_check=cancel_check,
                    on_step=on_step,
                )
            except Exception as exc:
                _LOGGER.exception("finalize job failed")
                final_status = "failed"
                error_message = str(exc)
                result = {
                    "status": "error",
                    "reportId": None,
                    "reportPath": None,
                    "libraryRevision": self.library_revision(),
                    "blockers": [],
                    "warnings": [],
                    "cleanup": {"previewedEmptyDirs": [], "removedEmptyDirs": []},
                    "errorMessage": error_message,
                }
            else:
                if cancel_check():
                    final_status = "cancelled"
                elif result.get("status") == "cancelled":
                    final_status = "cancelled"
                elif result.get("status") == "error":
                    final_status = "failed"
                    error_message = str(result.get("errorMessage") or "finalize error")

            if final_status == "succeeded" and result is not None:
                result_status = str(result.get("status", "error"))
                if result_status == "cancelled":
                    final_status = "cancelled"
                elif result_status == "error":
                    final_status = "failed"
                    error_message = str(result.get("errorMessage") or "finalize error")

            finished_at = _iso_now()
            with self._lock:
                started_at = self._finalize_job.get("startedAt")
                progress = int(self._finalize_job.get("progress", 0) or 0)
                if final_status == "succeeded" and result is not None:
                    self._finalize_last_status = str(result.get("status", "error"))
                    message = "처리 완료"
                    progress = 100
                elif final_status == "cancelled":
                    self._finalize_last_status = "idle"
                    message = "취소됨"
                elif final_status == "failed":
                    self._finalize_last_status = "error"
                    message = "처리 실패"
                else:
                    message = "처리 완료"

                self._finalize_job = build_finalize_job_snapshot(
                    job_id=self._finalize_job.get("jobId"),
                    status=final_status,
                    progress=progress,
                    message=message,
                    started_at=started_at if isinstance(started_at, str) else None,
                    finished_at=finished_at,
                    result=result,
                    error=error_message if final_status == "failed" else None,
                )
                self._pipeline_running = False
                self._pipeline_cancellable = False
                self._pipeline_phase = "idle"
                self._pipeline_percent = 0
                self._pipeline_label = "대기 중"
                self._finalize_running = False
                self._finalize_cancel_requested = False
                self._finalize_thread = None

        thread = threading.Thread(target=_worker, name="novelguard-finalize", daemon=True)
        with self._lock:
            self._finalize_thread = thread
        thread.start()

    def cancel_finalize(self) -> None:
        with self._lock:
            if not self._finalize_running:
                return
            self._finalize_cancel_requested = True
            self._cancel_requested = True

    def read_finalize_report(self, save_root: Path | None, report_id: str) -> dict[str, Any]:
        from application.finalize_report import read_finalize_report

        root = save_root if save_root is not None else self.finalize_save_root()
        return read_finalize_report(root, self.finalize_session_id(), report_id)

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
        self._move_ready_count = 0
        self._review_signal_count = 0
        self._approved_count = 0
        self._conflict_count = 0
        self._exact_auto_approved_count = 0
        self._files_by_id = {}
        self._clear_quality_cache()

    def _clear_quality_cache(self) -> None:
        self._quality_rows_cache = []
        self._integrity_issue_count = 0
        self._encoding_issue_count = 0
        self._small_file_anomaly_count = 0
        self._total_quality_issue_count = 0

    def _rebuild_review_index(
        self, files: list[FileRecord], *, sync_projection: bool = True
    ) -> None:
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
        self._refresh_duplicate_group_count()
        self._refresh_resolve_counts()
        if sync_projection:
            self._sync_file_review_projection()

    def _sync_file_review_projection(self) -> None:
        folder = self._index.folder_path
        if not folder:
            return
        from application.file_review_projection import build_file_review_projection

        rows = build_file_review_projection(self._review_rows_cache)
        self._index.replace_file_review_projection(folder, rows)

    def _refresh_duplicate_group_count(self) -> None:
        self._duplicate_group_count = sum(
            1 for row in self._review_rows_cache if row.get("rowKind") == "group"
        )

    def _refresh_resolve_counts(self) -> None:
        queue, approved, conflict = file_row_status_counts(self._review_rows_cache)
        move_ready, review_signal = resolve_insight_counts(self._review_rows_cache)
        self._queue_count = queue
        self._move_ready_count = move_ready
        self._review_signal_count = review_signal
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

    def _snapshot_relation_phase_inputs(
        self, folder: str, files: list[FileRecord]
    ) -> _RelationPhaseInputs:
        with self._lock:
            include_relation = self._settings.get_bool(SETTINGS_KEY_INCLUDE_RELATION)
            return _RelationPhaseInputs(
                folder=folder,
                files=tuple(files),
                files_by_id=dict(self._files_by_id),
                near_groups_by_id=dict(self._near_groups_by_id),
                library_revision=self._library_revision,
                include_relation=include_relation,
            )

    def _compute_relation_phase(self, inputs: _RelationPhaseInputs) -> _RelationPhaseResult | None:
        if not inputs.include_relation:
            return None

        from application.relation_batch_id import filename_set_digest, make_relation_batch_id
        from application.relation_membership import (
            build_exact_membership_by_file_id,
            build_near_membership_by_file_id,
        )
        from application.relation_review_rows_builder import build_relation_review_rows
        from application.review_state_merge import merge_review_state
        from domain.duplicate_exact import find_exact_duplicate_groups
        from domain.filename_relation import detect_filename_relations

        files = list(inputs.files)
        relation_batch_id = make_relation_batch_id(
            library_revision=inputs.library_revision,
            filename_set_digest_value=filename_set_digest(files),
        )
        result = detect_filename_relations(
            files,
            exact_membership_by_file_id=build_exact_membership_by_file_id(files),
            near_membership_by_file_id=build_near_membership_by_file_id(inputs.near_groups_by_id),
            relation_batch_id=relation_batch_id,
        )
        relation_groups_by_id = {group.group_id: group for group in result.groups}
        relation_skeleton = build_relation_review_rows(list(result.groups), inputs.files_by_id)
        stored = self._index.load_review_state(inputs.folder)
        exact_groups = find_exact_duplicate_groups(files)
        relation_rows = merge_review_state(
            relation_skeleton,
            stored,
            groups=exact_groups,
            files_by_id=inputs.files_by_id,
        )
        valid_group_ids = (
            {group.group_id for group in exact_groups}
            | set(inputs.near_groups_by_id.keys())
            | set(relation_groups_by_id.keys())
        )
        valid_file_ids = {file_record.id for file_record in files}
        return _RelationPhaseResult(
            relation_groups_by_id=relation_groups_by_id,
            relation_rows=relation_rows,
            valid_group_ids=valid_group_ids,
            valid_file_ids=valid_file_ids,
        )

    def _apply_relation_phase(
        self,
        folder: str,
        result: _RelationPhaseResult | None,
    ) -> None:
        with self._lock:
            self._strip_relation_rows()
            self._relation_groups_by_id = {}
            if result is None:
                return
            self._relation_groups_by_id = result.relation_groups_by_id
            self._review_rows_cache.extend(result.relation_rows)
        if result is not None:
            self._index.prune_review_state(folder, result.valid_group_ids, result.valid_file_ids)
            with self._lock:
                self._refresh_duplicate_group_count()
                self._refresh_resolve_counts()
            self._sync_file_review_projection()

    def _run_relation_phase(self, folder: str, files: list[FileRecord]) -> None:
        inputs = self._snapshot_relation_phase_inputs(folder, files)
        result = self._compute_relation_phase(inputs)
        self._apply_relation_phase(folder, result)

    def _snapshot_near_phase_inputs(self, folder: str, files: list[FileRecord]) -> _NearPhaseInputs:
        with self._lock:
            return _NearPhaseInputs(
                folder=folder,
                files=tuple(files),
                files_by_id=dict(self._files_by_id),
                library_revision=self._library_revision,
                scan_last_run=self._scan_last_run,
            )

    def _compute_near_phase(self, inputs: _NearPhaseInputs) -> _NearPhaseComputeResult:
        from application.near_batch_id import content_set_digest, make_near_batch_id
        from application.near_duplicate_detect import (
            build_exact_group_by_file_id,
            run_near_duplicate_detection,
        )
        from application.near_review_rows_builder import build_near_review_rows
        from application.review_state_merge import merge_review_state
        from domain.duplicate_exact import find_exact_duplicate_groups

        files = list(inputs.files)
        folder = inputs.folder
        near_batch_id = make_near_batch_id(
            library_revision=inputs.library_revision,
            folder_path=folder,
            content_set_digest_value=content_set_digest(files),
            scan_completed_at=inputs.scan_last_run,
        )
        exact_group_by_file_id = build_exact_group_by_file_id(files)
        large_library = len(files) >= scan_pipeline_constants.SCAN_NEAR_FAST_LIBRARY_THRESHOLD
        detection_result = run_near_duplicate_detection(
            root=Path(folder),
            files=files,
            near_batch_id=near_batch_id,
            exact_group_by_file_id=exact_group_by_file_id,
            large_library=large_library,
        )
        self._index.replace_near_duplicate_results(folder, detection_result)
        near_groups_by_id = {group.group_id: group for group in detection_result.groups}
        near_skeleton = build_near_review_rows(list(detection_result.groups), inputs.files_by_id)
        stored = self._index.load_review_state(folder)
        exact_groups = find_exact_duplicate_groups(files)
        near_rows = merge_review_state(
            near_skeleton,
            stored,
            groups=exact_groups,
            files_by_id=inputs.files_by_id,
        )
        valid_group_ids = {group.group_id for group in exact_groups} | set(near_groups_by_id.keys())
        valid_file_ids = {file_record.id for file_record in files}
        return _NearPhaseComputeResult(
            detection_result=detection_result,
            near_rows=near_rows,
            near_groups_by_id=near_groups_by_id,
            valid_group_ids=valid_group_ids,
            valid_file_ids=valid_file_ids,
        )

    def _apply_near_phase(self, folder: str, computed: _NearPhaseComputeResult) -> None:
        with self._lock:
            self._strip_near_rows()
            self._near_groups_by_id = computed.near_groups_by_id
            self._review_rows_cache.extend(computed.near_rows)
        self._index.prune_review_state(folder, computed.valid_group_ids, computed.valid_file_ids)
        with self._lock:
            self._refresh_duplicate_group_count()
            self._refresh_resolve_counts()
        self._sync_file_review_projection()

    def _run_near_duplicate_phase(self, folder: str, files: list[FileRecord]) -> None:
        inputs = self._snapshot_near_phase_inputs(folder, files)
        computed = self._compute_near_phase(inputs)
        self._apply_near_phase(folder, computed)

    def _restore_near_cache(self, folder: str, files: list[FileRecord]) -> None:
        result = self._index.load_near_duplicate_result(folder)
        if result is None or not result.groups:
            return
        self._merge_near_duplicate_result(folder, files, result)

    def _merge_near_duplicate_result(
        self,
        folder: str,
        files: list[FileRecord],
        result: Any,
    ) -> None:
        inputs = self._snapshot_near_phase_inputs(folder, files)
        from application.near_review_rows_builder import build_near_review_rows
        from application.review_state_merge import merge_review_state
        from domain.duplicate_exact import find_exact_duplicate_groups

        files_list = list(inputs.files)
        near_groups_by_id = {group.group_id: group for group in result.groups}
        near_skeleton = build_near_review_rows(list(result.groups), inputs.files_by_id)
        stored = self._index.load_review_state(folder)
        exact_groups = find_exact_duplicate_groups(files_list)
        near_rows = merge_review_state(
            near_skeleton,
            stored,
            groups=exact_groups,
            files_by_id=inputs.files_by_id,
        )
        computed = _NearPhaseComputeResult(
            detection_result=result,
            near_rows=near_rows,
            near_groups_by_id=near_groups_by_id,
            valid_group_ids={group.group_id for group in exact_groups}
            | set(near_groups_by_id.keys()),
            valid_file_ids={file_record.id for file_record in files_list},
        )
        self._apply_near_phase(folder, computed)

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

    def _set_pipeline_progress(self, percent: int, label: str) -> None:
        with self._lock:
            self._pipeline_percent = percent
            self._pipeline_label = label

    def _set_background_progress(
        self,
        *,
        phase: str,
        label: str,
        step: int,
        step_total: int,
        block_pipeline: bool = True,
    ) -> None:
        with self._lock:
            self._background_active = True
            self._background_phase = phase
            self._background_label = label
            self._background_step = step
            self._background_step_total = step_total
            if step_total <= 0:
                self._background_percent = 0
            else:
                self._background_percent = min(99, int((step / step_total) * 100))
            if block_pipeline:
                self._pipeline_phase = "analyze"
                self._pipeline_label = label
                self._pipeline_percent = self._background_percent
            self._pipeline_cancellable = False

    def _clear_background_progress(self) -> None:
        with self._lock:
            self._background_active = False
            self._background_phase = "idle"
            self._background_label = ""
            self._background_step = 0
            self._background_step_total = 0
            self._background_percent = 0

    def _pipeline_background_payload(self) -> dict[str, Any] | None:
        if not self._background_active:
            return None
        return {
            "active": True,
            "phase": self._background_phase,
            "label": self._background_label,
            "step": self._background_step,
            "stepTotal": self._background_step_total,
            "percent": self._background_percent,
        }

    def _set_exact_index_progress(self, label: str, percent: int) -> None:
        with self._lock:
            self._pipeline_phase = "exact_index"
            self._pipeline_label = label
            self._pipeline_percent = percent
            self._pipeline_cancellable = False

    def _run_scan(self, folder: str) -> None:
        scan_error: str | None = None
        probe_buffer: list[FileRecord] = []
        first_batch = True
        scan_file_total = 0

        def flush_batch() -> None:
            nonlocal probe_buffer, first_batch
            if not probe_buffer:
                return
            batch = probe_buffer
            probe_buffer = []
            reset = first_batch
            first_batch = False
            with self._lock:
                if self._pipeline_phase != "scan_persist":
                    self._pipeline_phase = "persist"
            self._index.append_files_batch(folder, batch, reset=reset)
            committed = self._index.file_count()
            with self._lock:
                if not self._index_ready and committed > 0:
                    self._index_ready = True
                self._library_revision += 1
            total = max(scan_file_total, 1)
            pct = min(100, int(committed * 100 / total))
            self._set_pipeline_progress(pct, f"인덱스 저장 중… ({committed}/{total})")

        def on_record(record: FileRecord) -> None:
            probe_buffer.append(record)
            if len(probe_buffer) >= scan_pipeline_constants.SCAN_PERSIST_BATCH_SIZE:
                flush_batch()

        def on_progress(pct: int, label: str) -> None:
            with self._lock:
                self._pipeline_phase = "probe"
            self._set_pipeline_progress(pct, label)

        def on_paths_collected(total: int) -> None:
            nonlocal scan_file_total
            scan_file_total = total

        def cancel_check() -> bool:
            return self._cancel_requested

        extension_raw, _ = self._settings.get_value(SETTINGS_KEY_SCAN_EXTENSION_FILTER)
        include_hidden = self._settings.get_bool(SETTINGS_KEY_SCAN_INCLUDE_HIDDEN)
        scan_cancelled = False
        try:
            extensions = parse_extension_filter(str(extension_raw))
            raw = self._scan_folder(
                folder,
                on_progress=on_progress,
                cancel_check=cancel_check,
                out=on_record,
                extensions=extensions,
                include_hidden=include_hidden,
                on_paths_collected=on_paths_collected,
            )
            scan_cancelled = bool(getattr(raw, "cancelled", False))
        except Exception as exc:
            scan_error = str(exc)

        if scan_error is not None:
            with self._lock:
                self._restore_backup_after_failed_scan(folder)
                self._pipeline_running = False
                self._pipeline_cancellable = False
                self._scan_thread = None
                self._pipeline_phase = "idle"
                self._pipeline_percent = 0
                self._pipeline_label = "오류"
                self._scan_state = "error"
            return

        if scan_cancelled:
            with self._lock:
                self._restore_backup_after_cancel(folder)
                self._pipeline_running = False
                self._pipeline_cancellable = False
                self._scan_thread = None
                self._pipeline_phase = "idle"
                self._pipeline_percent = 0
                had_prior = bool(self._backup_files)
                self._pipeline_label = "대기 중" if had_prior else "취소됨"
                self._scan_state = "success" if had_prior else "error"
            return

        with self._lock:
            self._pipeline_running = True
            self._pipeline_cancellable = False
            self._pipeline_phase = "scan_persist"
            self._pipeline_label = "인덱스 저장 중"

        flush_batch()

        with self._lock:
            self._post_scan_running = True
            self._pipeline_running = False
            self._scan_thread = None
            self._pipeline_phase = "exact_index"
            self._pipeline_label = "정확 중복 인덱스 준비 중…"
            self._pipeline_percent = 82
            self._pipeline_cancellable = False
            self._backup_files = None
            self._backup_folder = None
            self._deep_analysis_status = "running"
            self._deep_analysis_error = None

        self._start_post_scan_worker(folder)

    def _start_post_scan_worker(self, folder: str) -> None:
        def _worker() -> None:
            worker_t0 = log_phase_start("worker")
            worker_status = "complete"
            active_phase: str | None = None
            active_t0: float | None = None

            def _begin_phase(phase: str) -> None:
                nonlocal active_phase, active_t0
                if active_phase is not None and active_t0 is not None:
                    log_phase_end(active_phase, active_t0, status="complete")
                active_phase = phase
                active_t0 = log_phase_start(phase)

            def _finish_active_phase(*, status: str = "complete") -> None:
                nonlocal active_phase, active_t0
                if active_phase is not None and active_t0 is not None:
                    log_phase_end(active_phase, active_t0, status=status)
                active_phase = None
                active_t0 = None

            try:
                with self._lock:
                    self._deep_analysis_status = "running"
                    self._deep_analysis_error = None
                _begin_phase("exact_index")
                self._set_exact_index_progress("파일 메타데이터 로드 중…", 84)
                files = self._index.files()
                defer_projection = len(files) > 500
                step_total = 3 if defer_projection else 2

                self._set_exact_index_progress("정확 중복 그룹 계산 중…", 88)
                review_groups = find_exact_duplicate_groups(files)
                exact_auto_approved_count = 0
                if folder:
                    valid_group_ids = {group.group_id for group in review_groups}
                    valid_file_ids = {file_record.id for file_record in files}
                    self._index.prune_review_state(folder, valid_group_ids, valid_file_ids)
                    stored = self._index.load_review_state(folder)
                    exact_auto_approved_count = persist_exact_non_keeper_approvals(
                        folder, files, self._index, stored
                    )
                    stored = self._index.load_review_state(folder)
                    self._set_exact_index_progress("검토 행 구성 중…", 91)
                    review_rows = rebuild_rows_with_review_state(files, stored)
                else:
                    files_by_id = {file_record.id: file_record for file_record in files}
                    review_rows = build_review_rows(review_groups, files_by_id)

                self._set_exact_index_progress("품질 이슈 집계 중…", 94)
                with self._lock:
                    self._files_by_id = {f.id: f for f in files}
                self._rebuild_quality_index(folder, files)

                with self._lock:
                    self._review_rows_cache = review_rows
                    self._refresh_duplicate_group_count()
                    self._refresh_resolve_counts()
                    self._exact_auto_approved_count = exact_auto_approved_count
                    self._scan_state = "success"
                    self._scan_last_run = scan_timestamp()
                    self.bump_library_revision_unless_pending_apply()

                if defer_projection:
                    self._sync_file_review_projection()
                _finish_active_phase()

                deep_analysis_non_blocking = (
                    len(files) >= scan_pipeline_constants.SCAN_DEEP_ANALYSIS_BACKGROUND_THRESHOLD
                )
                if deep_analysis_non_blocking:
                    with self._lock:
                        self._pipeline_phase = "idle"
                        self._pipeline_label = "근사·관계 분석 중… (백그라운드)"
                        self._pipeline_percent = 0

                block_pipeline = not deep_analysis_non_blocking
                _begin_phase("queue")
                self._set_background_progress(
                    phase="queue",
                    label="중복·관계 분석 준비 중…",
                    step=0,
                    step_total=step_total,
                    block_pipeline=block_pipeline,
                )
                _finish_active_phase()

                _begin_phase("prepare")
                self._set_background_progress(
                    phase="prepare",
                    label="분석 대상 파일 준비 중…",
                    step=0,
                    step_total=step_total,
                    block_pipeline=block_pipeline,
                )
                _finish_active_phase()

                _begin_phase("relation")
                self._set_background_progress(
                    phase="relation",
                    label="파일명 관계 분석 중…",
                    step=1,
                    step_total=step_total,
                    block_pipeline=block_pipeline,
                )
                self._run_relation_phase(folder, files)
                self.bump_library_revision_unless_pending_apply()
                _finish_active_phase()

                _begin_phase("near")
                self._set_background_progress(
                    phase="near",
                    label="근사 중복 분석 중…",
                    step=2,
                    step_total=step_total,
                    block_pipeline=block_pipeline,
                )
                self._run_near_duplicate_phase(folder, files)
                self.bump_library_revision_unless_pending_apply()
                _finish_active_phase()

                if defer_projection:
                    _begin_phase("projection")
                    self._set_background_progress(
                        phase="projection",
                        label="검토 인덱스 동기화 중…",
                        step=3,
                        step_total=step_total,
                        block_pipeline=block_pipeline,
                    )
                    self._sync_file_review_projection()
                    _finish_active_phase()
            except Exception as exc:
                _LOGGER.exception("post-scan worker failed")
                worker_status = "error"
                _finish_active_phase(status="error")
                with self._lock:
                    self._scan_state = "error"
                    self._deep_analysis_status = "error"
                    self._deep_analysis_complete = False
                    self._deep_analysis_error = str(exc)
                    self._pipeline_phase = "idle"
                    self._pipeline_label = "후속 분석 실패"
                    self._pipeline_percent = 0
            else:
                with self._lock:
                    self._deep_analysis_status = "complete"
                    self._deep_analysis_complete = True
                    self._deep_analysis_error = None
                    self._pipeline_phase = "idle"
                    self._pipeline_percent = 100
                    self._pipeline_label = "대기 중"
            finally:
                with self._lock:
                    self._post_scan_running = False
                    self._clear_background_progress()
                self.bump_library_revision_unless_pending_apply()
                log_phase_end("worker", worker_t0, status=worker_status)

        threading.Thread(target=_worker, name="novelguard-post-scan", daemon=True).start()

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
