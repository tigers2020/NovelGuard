"""Verification pipeline: pytest → ruff → mypy → black (fail-fast)."""

from __future__ import annotations

import subprocess
import sys
from datetime import datetime
from pathlib import Path


def run_command(cmd: list[str], description: str, *, cwd: str) -> bool:
    print(f"\n{'=' * 60}")
    print(description)
    print(f"{'=' * 60}\n")
    print(" ".join(cmd), "\n")
    result = subprocess.run(cmd, cwd=cwd)
    return result.returncode == 0


def main() -> None:
    project_root = Path(__file__).resolve().parent.parent
    root = str(project_root)

    steps: list[tuple[list[str], str]] = [
        ([sys.executable, "-m", "pytest"], "1/4 python -m pytest"),
        ([sys.executable, "-m", "ruff", "check", "."], "2/4 python -m ruff check ."),
        ([sys.executable, "-m", "mypy", "src"], "3/4 python -m mypy src"),
        ([sys.executable, "-m", "black", "--check", "."], "4/4 python -m black --check ."),
    ]

    print("\nNovelGuard verification pipeline (fail-fast)")
    print(f"Time: {datetime.now().isoformat()}")
    print(f"Root: {project_root}")

    results: list[tuple[str, bool]] = []
    for cmd, label in steps:
        ok = run_command(cmd, label, cwd=root)
        results.append((label, ok))
        if not ok:
            break

    print(f"\n{'=' * 60}")
    print("Summary")
    print(f"{'=' * 60}")
    for label, ok in results:
        print(f"  {'PASS' if ok else 'FAIL'}: {label}")
    if len(results) < len(steps):
        for label, _ in steps[len(results) :]:
            print(f"  SKIP: {label}")

    failed = [label for label, ok in results if not ok]
    if failed:
        print(f"\nFailed at: {failed[0]}")
        sys.exit(1)
    print("\nAll steps passed.")
    sys.exit(0)


if __name__ == "__main__":
    main()
