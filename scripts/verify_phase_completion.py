"""Same verification pipeline as local dev / CI (fail-fast).

Order: ``pytest`` → ``ruff check .`` → ``mypy src`` → ``black --check .``

Excludes and tool config: ``pyproject.toml``. The working tree now contains
only the active test suite; disposed legacy tests live only in manual archive
bundles outside the normal verification path.
"""

from __future__ import annotations

import subprocess
import sys
from datetime import datetime
from pathlib import Path


def run_command(cmd: list[str], description: str, *, cwd: str) -> bool:
    """Run command; stream stdout/stderr. Return True if exit code is 0."""
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
    print("Step summary")
    print(f"{'=' * 60}")
    for label, ok in results:
        print(f"  {label}: {'PASS' if ok else 'FAIL'}")
    if len(results) < len(steps):
        for label, _ in steps[len(results) :]:
            print(f"  {label}: (skipped)")
    print(f"{'=' * 60}\n")

    all_ok = all(ok for _, ok in results) and len(results) == len(steps)
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
