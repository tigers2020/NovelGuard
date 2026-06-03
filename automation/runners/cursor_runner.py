"""Invoke Cursor CLI (cursor-agent / agent) with a prompt."""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class CursorRunResult:
    command: list[str]
    returncode: int
    stdout: str
    stderr: str
    dry_run: bool


def resolve_cli(cfg: dict[str, Any]) -> list[str]:
    cursor_cfg = cfg.get("cursor") or {}
    candidates = cursor_cfg.get("commands") or ["cursor-agent", "agent", "cursor"]
    for name in candidates:
        path = shutil.which(str(name))
        if path:
            return [path]
    raise FileNotFoundError(
        f"No Cursor CLI on PATH. Tried: {candidates}. Install: https://cursor.com/cli"
    )


def run_prompt(
    repo: Path,
    prompt: str,
    cfg: dict[str, Any],
) -> CursorRunResult:
    cursor_cfg = cfg.get("cursor") or {}
    if cursor_cfg.get("dry_run"):
        return CursorRunResult(
            command=["dry-run"],
            returncode=0,
            stdout="[dry_run] Cursor CLI skipped\n" + prompt[:2000],
            stderr="",
            dry_run=True,
        )

    base = resolve_cli(cfg)
    extra = [str(x) for x in (cursor_cfg.get("args") or ["-p"])]
    cmd = base + extra + [prompt]
    proc = subprocess.run(
        cmd,
        cwd=repo,
        text=True,
        capture_output=True,
    )
    return CursorRunResult(
        command=cmd,
        returncode=proc.returncode,
        stdout=proc.stdout or "",
        stderr=proc.stderr or "",
        dry_run=False,
    )
