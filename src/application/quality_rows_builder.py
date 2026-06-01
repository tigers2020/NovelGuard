"""Build QualityRow dicts from domain issues."""

from __future__ import annotations

from typing import Any

from domain.models import FileRecord
from domain.quality import QualityIssue

_KIND_TO_ISSUE_TYPE: dict[str, str] = {
    "empty_file": "small_file",
    "tiny_file": "small_file",
    "invalid_utf8": "encoding",
    "read_error": "integrity",
}

_KIND_TO_INTEGRITY: dict[str, str] = {
    "empty_file": "Empty file",
    "tiny_file": "Very small file",
    "invalid_utf8": "Decode error",
    "read_error": "Read error",
}


def quality_row_id(issue_id: str) -> str:
    return f"quality:{issue_id}"


def build_quality_rows(
    issues: list[QualityIssue],
    files_by_id: dict[str, FileRecord],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for issue in issues:
        record = files_by_id.get(issue.file_id)
        name = record.name if record is not None else _basename(issue.path)
        issue_type = _KIND_TO_ISSUE_TYPE[issue.kind]
        integrity = _KIND_TO_INTEGRITY[issue.kind]
        encoding = "UTF-8" if issue.kind not in ("invalid_utf8", "read_error") else "Unknown"
        rows.append(
            {
                "id": quality_row_id(issue.issue_id),
                "issueType": issue_type,
                "name": name,
                "path": issue.path,
                "encoding": encoding,
                "integrity": integrity,
                "severity": issue.severity,
                "suggestedAction": "Review manually",
            }
        )
    return rows


def _basename(path: str) -> str:
    return path.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
