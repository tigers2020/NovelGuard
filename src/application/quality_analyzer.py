"""Detect-only quality rules during scan (PR-14c)."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from domain.models import FileRecord
from domain.quality import QualityIssue, QualityKind, make_issue_id
from infrastructure.large_file_sampling import is_large_file, utf8_validate_path_sample

DEFAULT_TINY_THRESHOLD_BYTES = 128
ReadBytesFn = Callable[[Path], bytes]


def analyze_quality(
    folder_path: str,
    files: list[FileRecord],
    *,
    tiny_threshold_bytes: int = DEFAULT_TINY_THRESHOLD_BYTES,
    read_bytes: ReadBytesFn | None = None,
) -> list[QualityIssue]:
    root = Path(folder_path)
    reader = read_bytes or (lambda path: path.read_bytes())
    issues: list[QualityIssue] = []

    for record in files:
        issue = _analyze_file(
            root,
            record,
            tiny_threshold_bytes=tiny_threshold_bytes,
            read_bytes=reader,
        )
        if issue is not None:
            issues.append(issue)
    return issues


def _issue_from_scan_cache(
    record: FileRecord,
    *,
    tiny_threshold_bytes: int,
) -> QualityIssue | None:
    """Use scan-time encoding for stable outcomes; large invalid_utf8 is not re-read."""
    status = record.encoding_status
    if status is None:
        return None
    if status == "empty":
        return _make_issue(
            record,
            kind="empty_file",
            severity="error",
            message="File is empty",
            evidence={"size_bytes": 0},
        )
    if status == "utf-8":
        if record.size_bytes < tiny_threshold_bytes:
            return _make_issue(
                record,
                kind="tiny_file",
                severity="warning",
                message="File is very small",
                evidence={
                    "size_bytes": record.size_bytes,
                    "threshold_bytes": tiny_threshold_bytes,
                },
            )
        return None
    if status in ("invalid_utf8", "read_error"):
        return _issue_from_encoding_status(
            record,
            status,
            tiny_threshold_bytes=tiny_threshold_bytes,
        )
    return None


def _analyze_file(
    root: Path,
    record: FileRecord,
    *,
    tiny_threshold_bytes: int,
    read_bytes: ReadBytesFn,
) -> QualityIssue | None:
    cached = _issue_from_scan_cache(record, tiny_threshold_bytes=tiny_threshold_bytes)
    if cached is not None:
        return cached
    if record.encoding_status == "utf-8":
        return None

    path = root / record.relative_path

    if record.size_bytes == 0:
        return _make_issue(
            record,
            kind="empty_file",
            severity="error",
            message="File is empty",
            evidence={"size_bytes": 0},
        )

    if is_large_file(record.size_bytes):
        return _issue_from_encoding_status(
            record,
            utf8_validate_path_sample(path, record.size_bytes),
            tiny_threshold_bytes=tiny_threshold_bytes,
        )

    try:
        data = read_bytes(path)
    except OSError as exc:
        return _make_issue(
            record,
            kind="read_error",
            severity="error",
            message="Failed to read file",
            evidence={"error": str(exc), "size_bytes": record.size_bytes},
        )

    return _issue_from_encoding_status(
        record,
        "utf-8" if _bytes_utf8_valid(data) else "invalid_utf8",
        tiny_threshold_bytes=tiny_threshold_bytes,
    )


def _bytes_utf8_valid(data: bytes) -> bool:
    try:
        data.decode("utf-8")
        return True
    except UnicodeDecodeError:
        return False


def _issue_from_encoding_status(
    record: FileRecord,
    status: str,
    *,
    tiny_threshold_bytes: int,
) -> QualityIssue | None:
    if status == "read_error":
        return _make_issue(
            record,
            kind="read_error",
            severity="error",
            message="Failed to read file",
            evidence={"size_bytes": record.size_bytes},
        )
    if status == "invalid_utf8":
        return _make_issue(
            record,
            kind="invalid_utf8",
            severity="error",
            message="Invalid UTF-8 content",
            evidence={"size_bytes": record.size_bytes},
        )
    if record.size_bytes < tiny_threshold_bytes:
        return _make_issue(
            record,
            kind="tiny_file",
            severity="warning",
            message="File is very small",
            evidence={
                "size_bytes": record.size_bytes,
                "threshold_bytes": tiny_threshold_bytes,
            },
        )
    return None


def _make_issue(
    record: FileRecord,
    *,
    kind: QualityKind,
    severity: str,
    message: str,
    evidence: dict[str, Any],
) -> QualityIssue:
    issue_id = make_issue_id(record.id, kind)
    return QualityIssue(
        issue_id=issue_id,
        file_id=record.id,
        path=record.relative_path,
        severity=severity,  # type: ignore[arg-type]
        kind=kind,
        message=message,
        evidence=evidence,
    )
