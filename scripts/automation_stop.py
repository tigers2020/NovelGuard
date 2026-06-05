#!/usr/bin/env python3
"""Stop stale NovelGuard automation background processes (Windows).

Usage:
  python scripts/automation_stop.py
  python scripts/automation_stop.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

_PATTERNS = (
    "linear_webhook_handler.py",
    "automation_daemon.py",
    "automation_worker.py",
    "automation.runners.job_worker",
    "run-worker-loop.ps1",
    "run-automation.ps1",
)


def _find_pids() -> list[dict[str, str]]:
    ps = (
        "Get-CimInstance Win32_Process -Filter \"name='python.exe'\" | "
        "Where-Object { $_.CommandLine -match 'NovelGuard' -and "
        "($_.CommandLine -match 'linear_webhook|automation_daemon|automation_worker|job_worker') } | "
        "Select-Object ProcessId, CommandLine | ConvertTo-Json"
    )
    proc = subprocess.run(
        ["powershell", "-NoProfile", "-Command", ps],
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode != 0 or not (proc.stdout or "").strip():
        return []
    data = json.loads(proc.stdout)
    if isinstance(data, dict):
        data = [data]
    out: list[dict[str, str]] = []
    for row in data:
        cmd = str(row.get("CommandLine") or "")
        if not any(p in cmd for p in _PATTERNS):
            continue
        out.append({"pid": str(row.get("ProcessId")), "cmd": cmd})
    return out


def _kill_port_listeners(port: int) -> list[int]:
    ps = (
        f"Get-NetTCPConnection -LocalPort {port} -State Listen -ErrorAction SilentlyContinue | "
        "Select-Object -ExpandProperty OwningProcess -Unique"
    )
    proc = subprocess.run(
        ["powershell", "-NoProfile", "-Command", ps],
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
    )
    killed: list[int] = []
    for line in (proc.stdout or "").splitlines():
        line = line.strip()
        if not line.isdigit():
            continue
        pid = int(line)
        if pid <= 0:
            continue
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", f"Stop-Process -Id {pid} -Force"],
            check=False,
        )
        killed.append(pid)
    return killed


def main(argv: list[str] | None = None) -> int:
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root))

    parser = argparse.ArgumentParser(description="Stop stale NovelGuard automation processes")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--kill-port",
        action="store_true",
        help="Kill process listening on webhook port from config (default 8765)",
    )
    args = parser.parse_args(argv)

    if args.kill_port and not args.dry_run:
        try:
            from automation.runners.config import load_config

            cfg = load_config()
            port = int((cfg.get("linear") or {}).get("webhook_port") or 8765)
            killed = _kill_port_listeners(port)
            if killed:
                print(f"[stop] killed port {port} listeners: {killed}")
            else:
                print(f"[stop] no listener on port {port}")
        except Exception as exc:
            print(f"[stop] kill-port failed: {exc}", file=sys.stderr)

    rows = _find_pids()
    if not rows:
        print("[stop] no automation python processes found")
    else:
        for row in rows:
            print(f"[stop] pid={row['pid']} {row['cmd'][:120]}")
            if not args.dry_run:
                subprocess.run(
                    [
                        "powershell",
                        "-NoProfile",
                        "-Command",
                        f"Stop-Process -Id {row['pid']} -Force",
                    ],
                    check=False,
                )

    if not args.dry_run:
        try:
            from automation.runners.config import load_config
            from automation.runners.worker_lock import release_stale_locks

            cfg = load_config()
            cleared = release_stale_locks(cfg)
            if cleared:
                print(f"[stop] cleared locks: {', '.join(cleared)}")
        except Exception as exc:
            print(f"[stop] lock cleanup skipped: {exc}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
