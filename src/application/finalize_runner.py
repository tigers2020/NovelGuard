"""Finalize verification runner orchestration (PR-23)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

from application.finalize_blockers import (
    compute_finalize_blockers,
    compute_finalize_warnings,
    finalize_result_status,
)
from application.finalize_report import report_path_relative_to_save, write_finalize_report
from application.finalize_summary import build_finalize_summary, unique_file_ids_from_quality_issues
from application.ports.finalize_cleanup import FinalizeCleanupPort


def refresh_finalize_session_state(
    session: Any,
    *,
    reanalyze: Callable[[list[str]], None],
    quality_issues: Callable[[], list[Any]],
) -> None:
    session.refresh_resolve_counts()
    issue_file_ids = unique_file_ids_from_quality_issues(quality_issues())
    if issue_file_ids:
        reanalyze(issue_file_ids)


class FinalizeRunner:
    def __init__(
        self,
        *,
        cleanup: FinalizeCleanupPort,
        save_root: Path,
        audit_log_path: Path,
    ) -> None:
        self._cleanup = cleanup
        self._save_root = save_root
        self._audit_log_path = audit_log_path

    def run(
        self,
        session: Any,
        *,
        include_cleanup: bool,
        cancel_check: Callable[[], bool],
        on_step: Callable[[str, int, str], None],
    ) -> dict[str, Any]:
        on_step("precheck", 10, "사전 조건 확인")
        if cancel_check():
            return _cancelled_result(session)

        review_rows = session.review_rows_snapshot()
        blockers = _blockers_from_session(session, review_rows)
        warnings = _warnings_from_session(session, review_rows)

        on_step("reverify", 40, "상태 재검증")
        if cancel_check():
            return _cancelled_result(session)

        refresh_finalize_session_state(
            session,
            reanalyze=session.reanalyze_quality_for_file_ids,
            quality_issues=session.quality_issues,
        )
        review_rows = session.review_rows_snapshot()
        blockers = _blockers_from_session(session, review_rows)
        warnings = _warnings_from_session(session, review_rows)

        on_step("cleanup_preview", 70, "정리 미리보기")
        if cancel_check():
            return _cancelled_result(session)

        library_root = session.library_root_path()
        previewed: list[str] = []
        removed: list[str] = []
        if library_root is not None:
            previewed = self._cleanup.list_empty_dirs(str(library_root))
            if include_cleanup and not blockers:
                removed = self._cleanup.remove_empty_dirs(str(library_root), previewed)
                if removed:
                    session.increment_library_revision()

        on_step("report", 90, "보고서 저장")
        if cancel_check():
            return _cancelled_result(session)

        status = finalize_result_status(blockers, warnings)
        summary = build_finalize_summary(
            library_revision=session.library_revision(),
            scan_state=session.scan_state(),
            review_rows=review_rows,
            queue_count=session.queue_count(),
            conflict_count=session.conflict_count(),
            approved_count=session.approved_count(),
            has_pending_apply=session.has_pending_apply(),
            has_pending_quality_repair=session.has_pending_quality_repair(),
            encoding_issue_count=session.encoding_issue_count(),
            integrity_issue_count=session.integrity_issue_count(),
            small_file_anomaly_count=session.small_file_anomaly_count(),
            audit_log_path=self._audit_log_path,
        )
        cleanup_payload = {
            "previewedEmptyDirs": previewed,
            "removedEmptyDirs": removed,
        }
        revision = session.library_revision()
        session.set_finalize_counts(len(blockers), len(warnings))

        if status in ("blocked", "complete", "complete_with_warnings"):
            report_id, path = self._write_report(
                session=session,
                status=status,
                blockers=blockers,
                warnings=warnings,
                summary=summary,
                cleanup=cleanup_payload,
                library_revision=revision,
            )
            session.set_finalize_last_run(
                report_id=report_id,
                last_status=status,
                report_path=report_path_relative_to_save(self._save_root, path),
            )
            return {
                "status": status,
                "reportId": report_id,
                "reportPath": report_path_relative_to_save(self._save_root, path),
                "libraryRevision": revision,
                "blockers": blockers,
                "warnings": warnings,
                "cleanup": cleanup_payload,
            }

        return {
            "status": status,
            "reportId": None,
            "reportPath": None,
            "libraryRevision": revision,
            "blockers": blockers,
            "warnings": warnings,
            "cleanup": cleanup_payload,
        }

    def _write_report(
        self,
        *,
        session: Any,
        status: str,
        blockers: list[dict[str, Any]],
        warnings: list[dict[str, Any]],
        summary: dict[str, Any],
        cleanup: dict[str, Any],
        library_revision: int,
    ) -> tuple[str, Path]:
        document = {
            "reportId": None,
            "sessionId": session.finalize_session_id(),
            "createdAt": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "libraryRevision": library_revision,
            "status": status,
            "blockers": blockers,
            "warnings": warnings,
            "summary": summary,
            "audit": summary.get("auditTail", {}),
            "cleanup": cleanup,
        }
        return write_finalize_report(
            save_root=self._save_root,
            session_id=session.finalize_session_id(),
            document=document,
        )


def _blockers_from_session(session: Any, review_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return compute_finalize_blockers(
        review_rows=review_rows,
        scan_state=session.scan_state(),
        has_pending_apply=session.has_pending_apply(),
        has_pending_quality_repair=session.has_pending_quality_repair(),
        encoding_issue_count=session.encoding_issue_count(),
        integrity_issue_count=session.integrity_issue_count(),
    )


def _warnings_from_session(session: Any, review_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return compute_finalize_warnings(
        review_rows=review_rows,
        small_file_anomaly_count=session.small_file_anomaly_count(),
        encoding_issue_count=session.encoding_issue_count(),
    )


def _cancelled_result(session: Any) -> dict[str, Any]:
    review_rows = session.review_rows_snapshot()
    blockers = _blockers_from_session(session, review_rows)
    warnings = _warnings_from_session(session, review_rows)
    session.set_finalize_last_run(report_id=None, last_status="idle", report_path=None)
    return {
        "status": "cancelled",
        "reportId": None,
        "reportPath": None,
        "libraryRevision": session.library_revision(),
        "blockers": blockers,
        "warnings": warnings,
        "cleanup": {"previewedEmptyDirs": [], "removedEmptyDirs": []},
    }
