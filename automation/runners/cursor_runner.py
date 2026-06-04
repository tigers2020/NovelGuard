"""Invoke Cursor CLI (cursor-agent / agent) with a prompt."""

from __future__ import annotations

import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPTS_DIR = _REPO_ROOT / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))
from cursor_cli_common import apply_prompt_prefix, DEFAULT_PROMPT_PREFIX


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


def wrap_cursor_prompt(prompt: str, cfg: dict[str, Any]) -> str:
    cursor_cfg = cfg.get("cursor") or {}
    prefix = str(cursor_cfg.get("prompt_prefix", DEFAULT_PROMPT_PREFIX))
    return apply_prompt_prefix(prompt, prefix)


def run_prompt(
    repo: Path,
    prompt: str,
    cfg: dict[str, Any],
) -> CursorRunResult:
    cursor_cfg = cfg.get("cursor") or {}
    wrapped_prompt = wrap_cursor_prompt(prompt, cfg)
    if cursor_cfg.get("dry_run"):
        return CursorRunResult(
            command=["dry-run"],
            returncode=0,
            stdout="[dry_run] Cursor CLI skipped\n" + wrapped_prompt[:2000],
            stderr="",
            dry_run=True,
        )

    base = resolve_cli(cfg)
    extra = [str(x) for x in (cursor_cfg.get("args") or ["-p"])]
    cmd = base + extra + [wrapped_prompt]
    proc = subprocess.run(
        cmd,
        cwd=repo,
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
    )
    return CursorRunResult(
        command=cmd,
        returncode=proc.returncode,
        stdout=proc.stdout or "",
        stderr=proc.stderr or "",
        dry_run=False,
    )
