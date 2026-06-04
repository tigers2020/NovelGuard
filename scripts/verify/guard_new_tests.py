#!/usr/bin/env python3
"""Block staged additions of new test files unless ALLOW_NEW_TESTS=1."""

from __future__ import annotations

import os
import re
import subprocess
import sys

ALLOW_ENV = "ALLOW_NEW_TESTS"

TEST_PATTERNS = [
    re.compile(r"(^|/|\\)test_[^/\\]+\.py$"),
    re.compile(r"(^|/|\\)[^/\\]+_test\.py$"),
    re.compile(r".*\.(test|spec)\.(js|jsx|ts|tsx)$"),
]


def is_test_file(path: str) -> bool:
    normalized = path.replace("\\", "/")
    return any(p.search(normalized) for p in TEST_PATTERNS)


def staged_added_files() -> list[str]:
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-status", "--diff-filter=A"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )

    files: list[str] = []
    for line in result.stdout.splitlines():
        parts = line.split(maxsplit=1)
        if len(parts) == 2:
            files.append(parts[1])
    return files


def main() -> int:
    if os.environ.get(ALLOW_ENV) == "1":
        return 0

    try:
        added = staged_added_files()
    except subprocess.CalledProcessError as exc:
        print(exc.stderr or exc.stdout or "git diff failed", file=sys.stderr)
        return exc.returncode or 1
    except FileNotFoundError:
        print("git not found; cannot run test guard", file=sys.stderr)
        return 1

    blocked = [f for f in added if is_test_file(f)]

    if not blocked:
        return 0

    print("\nBlocked: new test files are not allowed by default.\n")
    for f in blocked:
        print(f"  - {f}")

    print(
        "\nTo allow this intentionally, rerun with:\n"
        f"  Unix:        {ALLOW_ENV}=1 git commit ...\n"
        f'  PowerShell:  $env:{ALLOW_ENV}="1"; git commit ...\n'
        "\nOnly use this after explicit user approval.\n"
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
