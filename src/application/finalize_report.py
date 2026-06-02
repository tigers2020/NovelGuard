"""Finalize report JSON read/write (PR-23)."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def finalize_report_root(save_root: Path, session_id: str) -> Path:
    return save_root / session_id


def write_finalize_report(
    *,
    save_root: Path,
    session_id: str,
    document: dict[str, Any],
) -> tuple[str, Path]:
    report_id = str(document.get("reportId") or f"finalize-{uuid.uuid4().hex}")
    document["reportId"] = report_id
    folder = finalize_report_root(save_root, session_id)
    folder.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    path = folder / f"finalize_{stamp}.json"
    path.write_text(json.dumps(document, ensure_ascii=False, indent=2), encoding="utf-8")
    return report_id, path


def read_finalize_report(save_root: Path, session_id: str, report_id: str) -> dict[str, Any]:
    folder = finalize_report_root(save_root, session_id)
    if not folder.is_dir():
        raise FileNotFoundError(report_id)
    for path in sorted(folder.glob("finalize_*.json"), reverse=True):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if isinstance(payload, dict) and payload.get("reportId") == report_id:
            return payload
    raise FileNotFoundError(report_id)


def report_path_relative_to_save(save_root: Path, absolute_path: Path) -> str:
    try:
        return absolute_path.resolve().relative_to(save_root.resolve()).as_posix()
    except ValueError:
        return absolute_path.as_posix()
