"""Runtime bridge DTO validators (mirror web/src/contracts)."""

from __future__ import annotations

import json
from typing import Any

FORBIDDEN_SNAPSHOT_ARRAY_KEYS = (
    "fileList",
    "reviewRows",
    "rows",
    "reviewRowsPage",
    "fileRows",
)

MAX_QUERY_LIMIT = 200
DEFAULT_QUERY_LIMIT = 100
FILE_ROW_MAX_QUERY_LIMIT = 500
FILE_ROW_DEFAULT_QUERY_LIMIT = 100


class SnapshotContractError(ValueError):
    pass


class PageContractError(ValueError):
    pass


class EmptySelectionError(ValueError):
    pass


class InvalidSelectionScopeError(ValueError):
    pass


class PreviewApplyError(ValueError):
    def __init__(self, reason: str, message: str | None = None) -> None:
        self.reason = reason
        super().__init__(message or reason)


class RepairPreviewError(ValueError):
    def __init__(self, reason: str, message: str | None = None) -> None:
        self.reason = reason
        super().__init__(message or reason)


class RepairApplyError(ValueError):
    def __init__(self, reason: str, message: str | None = None) -> None:
        self.reason = reason
        super().__init__(message or reason)


QUALITY_SORT_FIELDS = frozenset({"name", "path", "issueType", "severity", "encoding", "integrity"})

_PIPELINE_PHASES = frozenset(
    {"idle", "probe", "persist", "scan_persist", "exact_index", "analyze", "finalize"}
)

FILE_ROW_SORT_FIELDS = frozenset(
    {
        "name",
        "path",
        "extension",
        "size",
        "modifiedAt",
        "encoding",
        "duplicateGroup",
        "integrity",
    }
)


class QualityQueryError(ValueError):
    def __init__(self, reason: str, message: str | None = None) -> None:
        self.reason = reason
        super().__init__(message or reason)

    def __str__(self) -> str:
        return json.dumps({"reason": self.reason}, ensure_ascii=False)


class FileRowQueryError(ValueError):
    def __init__(self, reason: str, message: str | None = None) -> None:
        self.reason = reason
        super().__init__(message or reason)

    def __str__(self) -> str:
        return json.dumps({"reason": self.reason}, ensure_ascii=False)


class ApplyFailedError(ValueError):
    def __init__(
        self,
        reason: str,
        message: str | None = None,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.reason = reason
        self.details = details or {}
        super().__init__(message or reason)

    def __str__(self) -> str:
        return json.dumps({"reason": self.reason, "details": self.details}, ensure_ascii=False)


def validate_app_snapshot(snapshot: Any) -> None:
    if not isinstance(snapshot, dict):
        raise SnapshotContractError("AppSnapshot must be a dict")
    for key in (
        "route",
        "theme",
        "locale",
        "connection",
        "library",
        "pipeline",
        "work",
        "fileListSummary",
    ):
        if key not in snapshot:
            raise SnapshotContractError(f"AppSnapshot missing required field: {key}")
    for forbidden in FORBIDDEN_SNAPSHOT_ARRAY_KEYS:
        if forbidden in snapshot and isinstance(snapshot[forbidden], list):
            raise SnapshotContractError(f"AppSnapshot must not contain array field: {forbidden}")
    work = snapshot.get("work")
    if not isinstance(work, dict):
        raise SnapshotContractError("AppSnapshot.work must be a dict")
    scan = work.get("scan")
    if not isinstance(scan, dict):
        raise SnapshotContractError("AppSnapshot.work.scan must be a dict")
    for key in (
        "state",
        "lastRun",
        "indexReady",
        "deepAnalysisComplete",
        "deepAnalysisStatus",
        "deepAnalysisError",
    ):
        if key not in scan:
            raise SnapshotContractError(f"AppSnapshot.work.scan missing {key}")
    status = scan.get("deepAnalysisStatus")
    if status not in ("idle", "running", "complete", "error"):
        raise SnapshotContractError(f"invalid work.scan.deepAnalysisStatus: {status!r}")
    pipeline = snapshot.get("pipeline")
    if not isinstance(pipeline, dict):
        raise SnapshotContractError("AppSnapshot.pipeline must be a dict")
    phase = pipeline.get("phase")
    if not isinstance(phase, str) or phase not in _PIPELINE_PHASES:
        raise SnapshotContractError(f"invalid pipeline.phase: {phase!r}")
    background = pipeline.get("background")
    if background is not None:
        if not isinstance(background, dict):
            raise SnapshotContractError("AppSnapshot.pipeline.background must be a dict or null")
        if background.get("active"):
            for key in ("phase", "label", "step", "stepTotal", "percent"):
                if key not in background:
                    raise SnapshotContractError(f"AppSnapshot.pipeline.background missing {key}")
    resolve = work.get("resolve")
    if not isinstance(resolve, dict):
        raise SnapshotContractError("AppSnapshot.work.resolve must be a dict")
    if not isinstance(resolve.get("libraryRevision"), int):
        raise SnapshotContractError("ResolveSnapshot.libraryRevision must be a number")
    for key in ("moveReadyCount", "reviewSignalCount"):
        value = resolve.get(key)
        if not isinstance(value, int) or value < 0:
            raise SnapshotContractError(f"ResolveSnapshot.{key} must be a non-negative int")


def clamp_query_limit(query: dict[str, Any]) -> int:
    raw = int(query.get("limit") or DEFAULT_QUERY_LIMIT)
    return min(max(1, raw), MAX_QUERY_LIMIT)


def validate_review_rows_page(page: Any) -> None:
    if not isinstance(page, dict):
        raise PageContractError("ReviewRowsPage must be a dict")
    rows = page.get("rows")
    if not isinstance(rows, list) or len(rows) > MAX_QUERY_LIMIT:
        raise PageContractError("ReviewRowsPage.rows invalid or exceeds limit")
    if not isinstance(page.get("pageInfo"), dict) or not isinstance(page.get("summary"), dict):
        raise PageContractError("ReviewRowsPage.pageInfo or summary invalid")


def validate_file_rows_page(page: Any) -> None:
    if not isinstance(page, dict):
        raise PageContractError("FileRowsPage must be a dict")
    rows = page.get("rows")
    if not isinstance(rows, list) or len(rows) > FILE_ROW_MAX_QUERY_LIMIT:
        raise PageContractError("FileRowsPage.rows invalid or exceeds limit")
    page_info = page.get("pageInfo")
    if not isinstance(page_info, dict) or not isinstance(page_info.get("totalFiltered"), int):
        raise PageContractError("FileRowsPage.pageInfo invalid")


def validate_quality_rows_page(page: Any) -> None:
    if not isinstance(page, dict):
        raise PageContractError("QualityRowsPage must be a dict")
    rows = page.get("rows")
    if not isinstance(rows, list) or len(rows) > MAX_QUERY_LIMIT:
        raise PageContractError("QualityRowsPage.rows invalid or exceeds limit")


def validate_move_preview(payload: Any) -> None:
    if not isinstance(payload, dict):
        raise PageContractError("Move preview must be a dict")
    for key in (
        "previewToken",
        "libraryRevision",
        "selectionFingerprint",
        "hasPendingApply",
        "rows",
        "summary",
    ):
        if key not in payload:
            raise PageContractError(f"Move preview missing {key}")
    if not isinstance(payload.get("rows"), list):
        raise PageContractError("Move preview rows must be an array")
    if payload.get("hasPendingApply") is not True:
        raise PageContractError("Move preview hasPendingApply must be true")


_REVIEW_STATUSES = frozenset({"unreviewed", "approved", "conflict", "excluded"})
_PROPOSED_ACTIONS = frozenset({"keep", "move_duplicate", "move_organized", "ignore"})


def validate_duplicate_group_detail(payload: Any) -> None:
    if not isinstance(payload, dict):
        raise PageContractError("DuplicateGroupDetail must be a dict")
    status = payload.get("status")
    group_id = payload.get("groupId")
    if not isinstance(group_id, str):
        raise PageContractError("DuplicateGroupDetail.groupId must be a string")
    members = payload.get("members")
    if not isinstance(members, list):
        raise PageContractError("DuplicateGroupDetail.members must be a list")

    if status == "not_found":
        if payload.get("message") is None:
            raise PageContractError("not_found detail requires message")
        if members:
            raise PageContractError("not_found detail members must be empty")
        return

    if status != "ok":
        raise PageContractError("DuplicateGroupDetail.status must be ok or not_found")

    for key in ("type", "groupStatus", "keeperFileId", "keeperLabel", "evidence"):
        if key not in payload:
            raise PageContractError(f"DuplicateGroupDetail ok variant missing {key}")

    detail_type = payload.get("type")
    if detail_type not in ("exact", "near", "relation"):
        raise PageContractError("DuplicateGroupDetail.type must be exact, near, or relation")
    if payload.get("groupStatus") not in _REVIEW_STATUSES:
        raise PageContractError("DuplicateGroupDetail.groupStatus invalid")

    evidence = payload.get("evidence")
    if not isinstance(evidence, dict):
        raise PageContractError("DuplicateGroupDetail.evidence must be a dict")
    if detail_type == "exact":
        if evidence.get("matchKind") != "exact_content_hash":
            raise PageContractError("evidence.matchKind must be exact_content_hash")
        move_plan = payload.get("movePlan")
        if not isinstance(move_plan, dict):
            raise PageContractError("DuplicateGroupDetail.movePlan must be a dict")
    elif detail_type == "near":
        if evidence.get("matchKind") != "near_ngram_v1":
            raise PageContractError("evidence.matchKind must be near_ngram_v1")
        if not isinstance(evidence.get("maxSimilarity"), (int, float)):
            raise PageContractError("evidence.maxSimilarity must be a number")
        if not isinstance(evidence.get("threshold"), (int, float)):
            raise PageContractError("evidence.threshold must be a number")
    else:
        if evidence.get("matchKind") != "relation_filename_v1":
            raise PageContractError("evidence.matchKind must be relation_filename_v1")
        if evidence.get("relationKind") not in (
            "same_title_series",
            "chapter_sequence",
            "version_variant",
            "title_prefix_overlap",
        ):
            raise PageContractError("evidence.relationKind invalid")
        if evidence.get("confidenceLabel") not in ("low", "medium", "high"):
            raise PageContractError("evidence.confidenceLabel invalid")
        for list_key in ("normalizedNames", "matchedTokens", "differingTokens"):
            if not isinstance(evidence.get(list_key), list):
                raise PageContractError(f"evidence.{list_key} must be a list")

    if not isinstance(evidence.get("memberCount"), int):
        raise PageContractError("evidence.memberCount must be int")

    for member in members:
        if not isinstance(member, dict):
            raise PageContractError("DuplicateGroupDetail member must be a dict")
        for key in (
            "rowId",
            "fileId",
            "name",
            "path",
            "sizeBytes",
            "status",
            "isKeeper",
            "proposedAction",
            "integrity",
        ):
            if key not in member:
                raise PageContractError(f"DuplicateGroupDetail member missing {key}")
        if member.get("status") not in _REVIEW_STATUSES:
            raise PageContractError("member status invalid")
        if member.get("proposedAction") not in _PROPOSED_ACTIONS:
            raise PageContractError("member proposedAction invalid")
        integrity = member.get("integrity")
        if not isinstance(integrity, dict):
            raise PageContractError("member integrity must be a dict")
        if integrity.get("status") not in ("ok", "issue"):
            raise PageContractError("member integrity.status invalid")
        if not isinstance(integrity.get("label"), str):
            raise PageContractError("member integrity.label must be string")
        if not isinstance(integrity.get("issueCount"), int):
            raise PageContractError("member integrity.issueCount must be int")


_QUALITY_KINDS = frozenset({"empty_file", "tiny_file", "invalid_utf8", "read_error"})
_REPAIR_REASONS = frozenset(
    {"repair_not_implemented", "issue_not_repairable", "read_error", "ready"}
)
_ENCODING_CONFIDENCE = frozenset({"high", "low"})


def validate_quality_issue_detail(payload: Any) -> None:
    if not isinstance(payload, dict):
        raise PageContractError("QualityIssueDetailResponse must be a dict")
    status = payload.get("status")
    if status == "stale":
        raise PageContractError("QualityIssueDetailResponse must not use status stale in PR-21")
    if status == "not_found":
        if payload.get("message") != "quality_issue_not_found":
            raise PageContractError("not_found message must be quality_issue_not_found")
        if not isinstance(payload.get("id"), str):
            raise PageContractError("not_found id must be a string")
        return
    if status != "ok":
        raise PageContractError("QualityIssueDetailResponse.status must be ok or not_found")

    detail = payload.get("detail")
    if not isinstance(detail, dict):
        raise PageContractError("ok response requires detail object")

    for key in (
        "id",
        "libraryRevision",
        "issueType",
        "name",
        "path",
        "encoding",
        "integrity",
        "severity",
        "suggestedAction",
        "file",
        "evidence",
        "repairEligibility",
    ):
        if key not in detail:
            raise PageContractError(f"QualityIssueDetail.detail missing {key}")

    if detail.get("issueType") not in ("integrity", "encoding", "small_file"):
        raise PageContractError("detail.issueType invalid")
    if detail.get("severity") not in ("warning", "error"):
        raise PageContractError("detail.severity invalid")
    if not isinstance(detail.get("libraryRevision"), int):
        raise PageContractError("detail.libraryRevision must be int")

    file_block = detail.get("file")
    if not isinstance(file_block, dict):
        raise PageContractError("detail.file must be a dict")
    for key in ("fileId", "sizeBytes", "modifiedAtNs", "extension", "contentSha256"):
        if key not in file_block:
            raise PageContractError(f"detail.file missing {key}")

    evidence = detail.get("evidence")
    if not isinstance(evidence, dict):
        raise PageContractError("detail.evidence must be a dict")
    kind = evidence.get("kind")
    if kind not in _QUALITY_KINDS:
        raise PageContractError("detail.evidence.kind invalid")
    for key in ("message", "severity", "sizeBytes"):
        if key not in evidence:
            raise PageContractError(f"detail.evidence missing {key}")
    if kind == "tiny_file" and "thresholdBytes" not in evidence:
        raise PageContractError("tiny_file evidence requires thresholdBytes")

    repair = detail.get("repairEligibility")
    if not isinstance(repair, dict):
        raise PageContractError("detail.repairEligibility must be a dict")
    if not isinstance(repair.get("eligible"), bool):
        raise PageContractError("detail.repairEligibility.eligible must be bool")
    if repair.get("reason") not in _REPAIR_REASONS:
        raise PageContractError("detail.repairEligibility.reason invalid")
    if not isinstance(repair.get("label"), str):
        raise PageContractError("detail.repairEligibility.label must be string")


def validate_quality_repair_preview(payload: Any) -> None:
    if not isinstance(payload, dict):
        raise PageContractError("QualityRepairPreviewResult must be a dict")
    for key in (
        "repairPreviewToken",
        "libraryRevision",
        "issueSelectionFingerprint",
        "hasPendingQualityRepair",
        "rows",
        "summary",
    ):
        if key not in payload:
            raise PageContractError(f"QualityRepairPreviewResult missing {key}")
    if payload.get("hasPendingQualityRepair") is not True:
        raise PageContractError("hasPendingQualityRepair must be true")
    if not isinstance(payload.get("libraryRevision"), int):
        raise PageContractError("libraryRevision must be int")
    summary = payload.get("summary")
    if not isinstance(summary, dict):
        raise PageContractError("summary must be a dict")
    for key in ("issueCount", "operationCount"):
        if not isinstance(summary.get(key), int):
            raise PageContractError(f"summary.{key} must be int")
    rows = payload.get("rows")
    if not isinstance(rows, list):
        raise PageContractError("rows must be a list")
    for row in rows:
        if not isinstance(row, dict):
            raise PageContractError("preview row must be a dict")
        for key in ("issueId", "action", "relativePath", "sourceEncoding", "encodingConfidence"):
            if key not in row:
                raise PageContractError(f"preview row missing {key}")
        if row.get("action") != "utf8_convert":
            raise PageContractError("preview row action must be utf8_convert")
        if row.get("encodingConfidence") not in _ENCODING_CONFIDENCE:
            raise PageContractError("encodingConfidence invalid")
        if row.get("encodingConfidence") == "low" and not isinstance(
            row.get("encodingWarning"), str
        ):
            raise PageContractError("low confidence row requires encodingWarning")


class FinalizeError(Exception):
    def __init__(self, reason: str, details: str = "") -> None:
        self.reason = reason
        self.details = details
        super().__init__(reason)

    def __str__(self) -> str:
        return json.dumps({"reason": self.reason, "details": self.details}, ensure_ascii=False)


def validate_app_setting_response(payload: Any) -> None:
    if not isinstance(payload, dict):
        raise PageContractError("AppSettingResponse must be a dict")
    for key in ("key", "value", "source"):
        if key not in payload:
            raise PageContractError(f"AppSettingResponse missing {key}")
    if payload["source"] not in ("default", "persisted"):
        raise PageContractError("AppSettingResponse.source invalid")
    value = payload["value"]
    if not isinstance(value, (str, bool)):
        raise PageContractError("AppSettingResponse.value must be str or bool")


def validate_log_entries_page(payload: Any) -> None:
    if not isinstance(payload, dict):
        raise PageContractError("LogEntriesPage must be a dict")
    entries = payload.get("entries")
    if not isinstance(entries, list):
        raise PageContractError("LogEntriesPage.entries must be a list")
    for entry in entries:
        if not isinstance(entry, dict):
            raise PageContractError("LogEntry must be a dict")
        for key in ("timestamp", "level", "message"):
            if key not in entry:
                raise PageContractError(f"LogEntry missing {key}")
        if entry["level"] not in ("DEBUG", "INFO", "WARNING", "ERROR"):
            raise PageContractError("LogEntry.level invalid")
    page_info = payload.get("pageInfo")
    if not isinstance(page_info, dict):
        raise PageContractError("LogEntriesPage.pageInfo must be a dict")
    if page_info.get("hasMore") is not False:
        raise PageContractError("LogEntriesPage.pageInfo.hasMore must be false")


def validate_logs_artifacts_response(payload: Any) -> None:
    if not isinstance(payload, dict):
        raise PageContractError("LogsArtifactsResponse must be a dict")
    artifacts = payload.get("artifacts")
    if not isinstance(artifacts, list):
        raise PageContractError("LogsArtifactsResponse.artifacts must be a list")
    for item in artifacts:
        if not isinstance(item, dict):
            raise PageContractError("LogsArtifact must be a dict")
        for key in ("id", "kind", "label", "path"):
            if key not in item:
                raise PageContractError(f"LogsArtifact missing {key}")
        if item["kind"] not in (
            "audit_tail",
            "finalize_report",
            "packaging_log",
            "unknown",
        ):
            raise PageContractError("LogsArtifact.kind invalid")


def validate_app_info(payload: Any) -> None:
    if not isinstance(payload, dict):
        raise PageContractError("AppInfo must be a dict")
    required = (
        "appName",
        "version",
        "buildType",
        "gitCommit",
        "builtAt",
        "frontendBuild",
        "pythonRuntime",
    )
    for key in required:
        if key not in payload:
            raise PageContractError(f"AppInfo missing {key}")
    if payload["buildType"] not in ("dev", "production", "packaged"):
        raise PageContractError("AppInfo.buildType invalid")
    if not isinstance(payload["appName"], str) or not isinstance(payload["version"], str):
        raise PageContractError("AppInfo appName/version must be str")


def validate_finalize_summary(payload: Any) -> None:
    if not isinstance(payload, dict):
        raise PageContractError("FinalizeSummary must be a dict")
    resolve = payload.get("resolve")
    if not isinstance(resolve, dict):
        raise PageContractError("FinalizeSummary.resolve must be a dict")
    if not isinstance(resolve.get("exactUnresolvedQueueCount"), int):
        raise PageContractError("exactUnresolvedQueueCount must be int")
    if not isinstance(payload.get("blockers"), list) or not isinstance(
        payload.get("warnings"), list
    ):
        raise PageContractError("FinalizeSummary blockers/warnings must be lists")


def validate_finalize_cleanup_preview(payload: Any) -> None:
    if not isinstance(payload, dict):
        raise PageContractError("FinalizeCleanupPreview must be a dict")
    previewed = payload.get("previewedEmptyDirs")
    if not isinstance(previewed, list) or not all(isinstance(item, str) for item in previewed):
        raise PageContractError("previewedEmptyDirs must be a list of strings")


def validate_finalize_result(payload: Any) -> None:
    if not isinstance(payload, dict):
        raise PageContractError("FinalizeResult must be a dict")
    status = payload.get("status")
    if status not in (
        "complete",
        "complete_with_warnings",
        "blocked",
        "cancelled",
        "error",
    ):
        raise PageContractError("FinalizeResult.status invalid")
    if status in ("complete", "complete_with_warnings", "blocked"):
        if not isinstance(payload.get("reportId"), str) or not isinstance(
            payload.get("reportPath"), str
        ):
            raise PageContractError("FinalizeResult report fields required")
    else:
        if payload.get("reportId") is not None or payload.get("reportPath") is not None:
            raise PageContractError("FinalizeResult report fields must be null")
    cleanup = payload.get("cleanup")
    if not isinstance(cleanup, dict):
        raise PageContractError("FinalizeResult.cleanup must be a dict")
    for key in ("previewedEmptyDirs", "removedEmptyDirs"):
        if not isinstance(cleanup.get(key), list):
            raise PageContractError(f"cleanup.{key} must be a list")


def validate_selection_scope(selection: Any) -> None:
    if not isinstance(selection, dict):
        raise InvalidSelectionScopeError("SelectionScope must be a dict")
    scope_type = selection.get("type")
    if scope_type == "explicit_rows":
        row_ids = selection.get("rowIds")
        if not isinstance(row_ids, list) or len(row_ids) == 0:
            raise EmptySelectionError()
        return
    if scope_type == "current_query":
        query = selection.get("query")
        if not isinstance(query, dict) or not query.get("viewMode"):
            raise InvalidSelectionScopeError(
                "current_query requires a ReviewRowsQuery with viewMode"
            )
        if not isinstance(selection.get("excludeRowIds"), list):
            raise InvalidSelectionScopeError("excludeRowIds must be an array")
        return
    raise InvalidSelectionScopeError(f"Unknown SelectionScope type: {scope_type}")
