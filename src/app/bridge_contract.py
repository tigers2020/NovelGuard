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
    resolve = work.get("resolve")
    if not isinstance(resolve, dict) or not isinstance(resolve.get("libraryRevision"), int):
        raise SnapshotContractError("ResolveSnapshot.libraryRevision must be a number")


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
    if detail_type not in ("exact", "near"):
        raise PageContractError("DuplicateGroupDetail.type must be exact or near")
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
    else:
        if evidence.get("matchKind") != "near_ngram_v1":
            raise PageContractError("evidence.matchKind must be near_ngram_v1")
        if not isinstance(evidence.get("maxSimilarity"), (int, float)):
            raise PageContractError("evidence.maxSimilarity must be a number")
        if not isinstance(evidence.get("threshold"), (int, float)):
            raise PageContractError("evidence.threshold must be a number")

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
