"""Block branch-mutating git commands for AI agent subprocesses."""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

ALLOW_ENV = "NOVELGUARD_ALLOW_GIT_BRANCH_OPS"
REAL_GIT_ENV = "GIT_GUARD_REAL_GIT"


def git_guard_bin_dir() -> Path:
    from automation.runners.config import repo_root

    return repo_root() / ".automation" / "bin"


def guard_allowed() -> bool:
    return os.environ.get(ALLOW_ENV) == "1"


def _positional_before_ddash(args: list[str]) -> list[str]:
    out: list[str] = []
    i = 0
    while i < len(args):
        token = args[i]
        if token == "--":
            break
        if token.startswith("-"):
            if token in ("-b", "-B", "--branch") and i + 1 < len(args):
                i += 2
                continue
            i += 1
            continue
        out.append(token)
        i += 1
    return out


def forbidden_git_reason(args: list[str]) -> str | None:
    """Return reason string if git args must be blocked for agents."""
    if guard_allowed() or not args:
        return None

    subcmd = args[0]
    rest = args[1:]

    if subcmd in {"-h", "--help", "help"}:
        return None

    if subcmd == "merge":
        return "merge"

    if subcmd == "rebase":
        return "rebase"

    if subcmd == "worktree" and "add" in rest:
        return "worktree add"

    if subcmd == "reset" and "--hard" in rest:
        return "reset --hard"

    if subcmd == "switch":
        if "-c" in rest or "--create" in rest:
            return "switch -c"
        if "-h" in rest or "--help" in rest:
            return None
        if _positional_before_ddash(rest):
            return "switch"
        return None

    if subcmd == "checkout":
        if "-b" in rest or "-B" in rest or "--branch" in rest:
            return "checkout -b"
        if "-h" in rest or "--help" in rest:
            return None
        if "--" in rest:
            return None
        if _positional_before_ddash(rest):
            return "checkout"
        return None

    if subcmd == "branch":
        if any(flag in rest for flag in ("-D", "-d", "--delete", "-m", "-M", "-c", "-C")):
            return "branch mutate"
        if "--show-current" in rest:
            return None
        pos = _positional_before_ddash(rest)
        if not pos:
            return None
        list_only = {
            "--contains",
            "--no-contains",
            "--merged",
            "--no-merged",
            "--points-at",
            "--format",
        }
        if list_only.intersection(rest):
            return None
        return "branch <name>"

    return None


def find_real_git() -> str:
    override = os.environ.get(REAL_GIT_ENV)
    if override:
        return override

    guard_bin = git_guard_bin_dir().resolve()
    path_key = "PATH"
    for part in os.environ.get(path_key, "").split(os.pathsep):
        if not part:
            continue
        try:
            if Path(part).resolve() == guard_bin:
                continue
        except OSError:
            pass
        for name in ("git.exe", "git") if sys.platform == "win32" else ("git",):
            candidate = Path(part) / name
            if candidate.is_file():
                return str(candidate)

    found = shutil.which("git")
    return found or "git"


def prepend_git_guard_path(env: dict[str, str] | None = None) -> dict[str, str]:
    """Copy env with ``.automation/bin`` prepended so ``git`` hits the guard wrapper."""
    merged = dict(env if env is not None else os.environ)
    bin_dir = str(git_guard_bin_dir().resolve())
    path_key = "PATH"
    current = merged.get(path_key, "")
    parts = [p for p in current.split(os.pathsep) if p]
    if not parts or Path(parts[0]).resolve() != Path(bin_dir):
        merged[path_key] = os.pathsep.join([bin_dir, *parts])
    return merged


def branch_change_error(start_branch: str, end_branch: str) -> str | None:
    if start_branch == end_branch:
        return None
    return (
        f"Job failed: branch changed from {start_branch!r} to {end_branch!r}. "
        "Do not continue automation."
    )
