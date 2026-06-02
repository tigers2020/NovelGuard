"""Logs artifact metadata listing (PR-28)."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def _artifact_id(kind: str, path: Path) -> str:
    digest = hashlib.sha256(f"{kind}:{path}".encode("utf-8")).hexdigest()
    return digest[:16]


def _mtime_iso(path: Path) -> str | None:
    try:
        mtime = path.stat().st_mtime
    except OSError:
        return None
    return datetime.fromtimestamp(mtime, tz=UTC).isoformat().replace("+00:00", "Z")


def list_logs_artifacts(
    *,
    audit_log_path: Path | None,
    finalize_save_root: Path | None,
    finalize_session_id: str | None,
    packaging_log_path: Path | None = None,
    max_finalize_reports: int = 5,
) -> dict[str, Any]:
    artifacts: list[dict[str, Any]] = []

    if audit_log_path is not None and audit_log_path.is_file():
        stat = audit_log_path.stat()
        artifacts.append(
            {
                "id": _artifact_id("audit_tail", audit_log_path),
                "kind": "audit_tail",
                "label": "Apply audit log",
                "path": str(audit_log_path.resolve()),
                "createdAt": _mtime_iso(audit_log_path),
                "sizeBytes": stat.st_size,
            }
        )

    if finalize_save_root is not None and finalize_session_id:
        report_dir = finalize_save_root / finalize_session_id
        if report_dir.is_dir():
            report_paths = sorted(report_dir.glob("finalize_*.json"), reverse=True)
            for path in report_paths[:max_finalize_reports]:
                stat = path.stat()
                artifacts.append(
                    {
                        "id": _artifact_id("finalize_report", path),
                        "kind": "finalize_report",
                        "label": path.name,
                        "path": str(path.resolve()),
                        "createdAt": _mtime_iso(path),
                        "sizeBytes": stat.st_size,
                    }
                )

    if packaging_log_path is not None and packaging_log_path.is_file():
        stat = packaging_log_path.stat()
        artifacts.append(
            {
                "id": _artifact_id("packaging_log", packaging_log_path),
                "kind": "packaging_log",
                "label": "Packaging log",
                "path": str(packaging_log_path.resolve()),
                "createdAt": _mtime_iso(packaging_log_path),
                "sizeBytes": stat.st_size,
            }
        )

    return {"artifacts": artifacts}
