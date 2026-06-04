#!/usr/bin/env python3
"""Launch packaged exe briefly; PASS if process stays alive (no GUI assertions)."""

from __future__ import annotations

import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXE = ROOT / "dist" / "NovelGuard" / "NovelGuard.exe"
MANIFEST = ROOT / "dist" / "NovelGuard" / "build-manifest.json"
ALIVE_SECONDS = 8


def main() -> int:
    if not EXE.is_file():
        print(f"FAIL: missing {EXE}")
        return 1
    if not MANIFEST.is_file():
        print(f"FAIL: missing {MANIFEST}")
        return 1

    proc = subprocess.Popen(
        [str(EXE)],
        cwd=str(EXE.parent),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(ALIVE_SECONDS)
    rc = proc.poll()
    if rc is not None:
        print(f"FAIL: NovelGuard.exe exited early (code {rc})")
        return 1

    proc.terminate()
    try:
        proc.wait(timeout=15)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=5)

    print(f"PASS: NovelGuard.exe alive >= {ALIVE_SECONDS}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
