"""Verification pipeline: pytest → ruff → mypy → black → npm lint → npm test → verify_packaging (fail-fast)."""

from __future__ import annotations

import shutil
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

    npm = shutil.which("npm")
    if npm is None:
        print("ERROR: npm not found on PATH; required for web lint step.")
        sys.exit(1)

    verify_packaging = project_root / "scripts" / "verify_packaging.py"
    fixture_smoke = project_root / "scripts" / "fixture_library_smoke.py"
    launch_smoke = project_root / "scripts" / "launch_packaged_smoke.py"
    packaged_exe = project_root / "dist" / "NovelGuard" / "NovelGuard.exe"
    web_dir = project_root / "web"
    steps: list[tuple[list[str], str]] = [
        ([sys.executable, "-m", "pytest"], "1/9 python -m pytest"),
        ([sys.executable, "-m", "ruff", "check", "."], "2/9 python -m ruff check ."),
        ([sys.executable, "-m", "mypy", "src"], "3/9 python -m mypy src"),
        ([sys.executable, "-m", "black", "--check", "."], "4/9 python -m black --check ."),
        ([npm, "run", "lint"], "5/9 npm run lint"),
        ([npm, "run", "test"], "6/9 npm run test (web vitest)"),
        (
            [sys.executable, str(verify_packaging)],
            "7/9 packaging verification (static; no PyInstaller run)",
        ),
        (
            [sys.executable, str(fixture_smoke)],
            "8/9 fixture library smoke (headless)",
        ),
    ]
    if packaged_exe.is_file():
        steps.append(
            (
                [sys.executable, str(launch_smoke)],
                "9/9 packaged exe launch smoke",
            )
        )

    print("\nNovelGuard verification pipeline (fail-fast)")
    print(f"Time: {datetime.now().isoformat()}")
    print(f"Root: {project_root}")

    results: list[tuple[str, bool]] = []
    for cmd, label in steps:
        step_cwd = str(web_dir) if "npm run test" in label else root
        ok = run_command(cmd, label, cwd=step_cwd)
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
