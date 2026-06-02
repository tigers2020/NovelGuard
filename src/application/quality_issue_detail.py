"""Build QualityIssueDetailResponse from scan snapshot (PR-21)."""

from __future__ import annotations

from typing import Any

from domain.models import FileRecord
from domain.quality import QualityIssue, QualityKind

_NOT_FOUND_MESSAGE = "quality_issue_not_found"
_QUALITY_PREFIX = "quality:"


def normalize_quality_issue_id(issue_id: str) -> str | None:
    """Prefix correction only; return None for malformed ids (never promote arbitrary strings)."""
    trimmed = issue_id.strip()
    if not trimmed:
        return None
    if trimmed.startswith(_QUALITY_PREFIX):
        payload = trimmed[len(_QUALITY_PREFIX) :]
        if not payload or payload.startswith(_QUALITY_PREFIX):
            return None
        return f"{_QUALITY_PREFIX}{payload}"
    return f"{_QUALITY_PREFIX}{trimmed}"


def not_found_id_for_request(issue_id: str) -> str:
    """Normalized id for not_found payloads (malformed → best-effort single prefix)."""
    normalized = normalize_quality_issue_id(issue_id)
    if normalized is not None:
        return normalized
    trimmed = issue_id.strip()
    if trimmed.startswith(_QUALITY_PREFIX):
        return trimmed
    return f"{_QUALITY_PREFIX}{trimmed}" if trimmed else _QUALITY_PREFIX


def build_quality_issue_detail(
    issue_id: str,
    *,
    quality_rows: list[dict[str, Any]],
    quality_issues: list[QualityIssue],
    files_by_id: dict[str, FileRecord],
    library_revision: int,
) -> dict[str, Any]:
    normalized = normalize_quality_issue_id(issue_id)
    if normalized is None:
        return {
            "status": "not_found",
            "id": not_found_id_for_request(issue_id),
            "message": _NOT_FOUND_MESSAGE,
        }

    row = next((r for r in quality_rows if r.get("id") == normalized), None)
    if row is None:
        return {
            "status": "not_found",
            "id": normalized,
            "message": _NOT_FOUND_MESSAGE,
        }

    domain_id = normalized[len(_QUALITY_PREFIX) :]
    issue = next((i for i in quality_issues if i.issue_id == domain_id), None)
    if issue is None:
        return {
            "status": "not_found",
            "id": normalized,
            "message": _NOT_FOUND_MESSAGE,
        }

    record = files_by_id.get(issue.file_id)
    if record is None:
        return {
            "status": "not_found",
            "id": normalized,
            "message": _NOT_FOUND_MESSAGE,
        }

    return {
        "status": "ok",
        "detail": _build_ok_detail(
            normalized=normalized,
            row=row,
            issue=issue,
            record=record,
            library_revision=library_revision,
        ),
    }


def _build_ok_detail(
    *,
    normalized: str,
    row: dict[str, Any],
    issue: QualityIssue,
    record: FileRecord,
    library_revision: int,
) -> dict[str, Any]:
    kind = issue.kind
    encoding = row.get("encoding") or _encoding_for_kind(kind)
    return {
        "id": normalized,
        "libraryRevision": library_revision,
        "issueType": row["issueType"],
        "name": row.get("name") or record.name,
        "path": issue.path,
        "encoding": encoding,
        "integrity": row["integrity"],
        "severity": issue.severity,
        "suggestedAction": row.get("suggestedAction") or "Review manually",
        "file": {
            "fileId": record.id,
            "sizeBytes": record.size_bytes,
            "modifiedAtNs": record.modified_at_ns,
            "extension": record.extension,
            "contentSha256": record.content_sha256 or "",
        },
        "evidence": _build_evidence(issue, record),
        "repairEligibility": _repair_eligibility_for_kind(kind),
    }


def _encoding_for_kind(kind: QualityKind) -> str:
    if kind in ("invalid_utf8", "read_error"):
        return "Unknown"
    return "UTF-8"


def _build_evidence(issue: QualityIssue, record: FileRecord) -> dict[str, Any]:
    base: dict[str, Any] = {
        "kind": issue.kind,
        "message": issue.message,
        "severity": issue.severity,
        "sizeBytes": record.size_bytes,
    }
    ev = issue.evidence
    if issue.kind == "empty_file":
        return {**base, "sizeBytes": int(ev.get("size_bytes", 0))}
    if issue.kind == "tiny_file":
        return {
            **base,
            "thresholdBytes": int(ev.get("threshold_bytes", 0)),
        }
    if issue.kind == "invalid_utf8":
        out: dict[str, Any] = {**base}
        decode_error = ev.get("decode_error")
        if decode_error is not None:
            out["decodeError"] = str(decode_error)
        return out
    if issue.kind == "read_error":
        out = {**base}
        error = ev.get("error")
        if error is not None:
            out["error"] = str(error)
        return out
    return base


def _repair_eligibility_for_kind(kind: QualityKind) -> dict[str, Any]:
    if kind == "invalid_utf8":
        return {
            "eligible": True,
            "reason": "ready",
            "futureAction": "utf8_convert",
            "label": "UTF-8 repair available",
        }
    if kind == "read_error":
        return {
            "eligible": False,
            "reason": "read_error",
            "label": "Cannot repair read errors automatically",
        }
    return {
        "eligible": False,
        "reason": "issue_not_repairable",
        "label": "Manual review required",
    }
