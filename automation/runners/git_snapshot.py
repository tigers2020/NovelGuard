"""Best-effort git working tree snapshot for TUI agent panel."""

from __future__ import annotations

import subprocess
from pathlib import Path


def read_git_status_short(
    repo_path: str | None,
    *,
    max_lines: int = 10,
) -> tuple[int, list[str]]:
    """Return (total changed entry count, up to ``max_lines`` status lines)."""
    if not repo_path:
        return 0, []
    repo = Path(repo_path)
    if not repo.is_dir():
        return 0, []
    try:
        proc = subprocess.run(
            ["git", "status", "--short"],
            cwd=repo,
            text=True,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return 0, []
    if proc.returncode != 0:
        return 0, []
    lines = [ln for ln in (proc.stdout or "").splitlines() if ln.strip()]
    if len(lines) <= max_lines:
        return len(lines), lines
    extra = len(lines) - max_lines
    return len(lines), [*lines[:max_lines], f"... +{extra} more"]
