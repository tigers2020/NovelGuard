#!/usr/bin/env python3
"""Run beta smoke scripts (no full pytest gate)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXE = ROOT / "dist" / "NovelGuard" / "NovelGuard.exe"


def run(label: str, script: str, extra: list[str] | None = None) -> bool:
    cmd = [sys.executable, str(ROOT / "scripts" / script), *(extra or [])]
    print(f"\n== {label} ==")
    result = subprocess.run(cmd, cwd=str(ROOT))
    return result.returncode == 0


def main() -> int:
    steps = [
        ("verify_packaging", "verify_packaging.py", None),
        ("fixture_library", "fixture_library_smoke.py", None),
    ]
    if EXE.is_file():
        steps.append(("launch_exe", "launch_packaged_smoke.py", None))
    else:
        print("skip launch_packaged_smoke (no dist/NovelGuard/NovelGuard.exe)")

    failed: list[str] = []
    for label, script, extra in steps:
        if not run(label, script, extra):
            failed.append(label)

    if failed:
        print(f"\nFAIL: {', '.join(failed)}")
        return 1
    print("\nAll beta_gate steps passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
