#!/usr/bin/env python3
"""Git wrapper: block branch ops for AI agents unless explicitly allowed."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from automation.runners.git_guard import (  # noqa: E402
    ALLOW_ENV,
    find_real_git,
    forbidden_git_reason,
)


def main(argv: list[str] | None = None) -> int:
    args = list(argv if argv is not None else sys.argv[1:])
    reason = forbidden_git_reason(args)
    if reason is not None:
        print(
            f"[git-guard] blocked forbidden git command: git {' '.join(args)} ({reason})",
            file=sys.stderr,
        )
        print(
            f"[git-guard] Set {ALLOW_ENV}=1 only for human-approved branch operations.",
            file=sys.stderr,
        )
        return 2

    real_git = find_real_git()
    return subprocess.call([real_git, *args])


if __name__ == "__main__":
    raise SystemExit(main())
