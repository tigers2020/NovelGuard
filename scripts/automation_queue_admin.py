#!/usr/bin/env python3
"""Inspect and repair the automation job queue."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root))

    from automation.runners.config import load_config, repo_root
    from automation.runners.queue import JobQueue
    from automation.runners.worker_lock import (
        clear_lock,
        clear_stale_file_lock,
        lock_holder_alive,
    )

    parser = argparse.ArgumentParser(description="Automation queue admin")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("status", help="Show queued/running jobs")

    release_p = sub.add_parser("release", help="Re-queue or fail stuck running jobs")
    release_p.add_argument("--job-id", help="Specific job_id to release")
    release_p.add_argument("--force", action="store_true")
    release_p.add_argument("--stale-seconds", type=float, default=120.0)

    locks_p = sub.add_parser("release-locks", help="Clear stale repo/worker lock files")
    locks_p.add_argument("--force", action="store_true")

    reset_p = sub.add_parser("reset", help="Delete job row so webhook can re-enqueue same job_id")
    reset_p.add_argument("--job-id", required=True)

    args = parser.parse_args(argv)
    cfg = load_config()
    queue_path = Path(cfg.get("queue", {}).get("path", "automation/jobs/queue.sqlite"))
    if not queue_path.is_absolute():
        queue_path = repo_root() / queue_path

    locks_dir = Path(cfg.get("locks", {}).get("dir", "automation/locks"))
    if not locks_dir.is_absolute():
        locks_dir = repo_root() / locks_dir

    stale = cfg.get("queue", {}).get("stale_seconds")
    queue = JobQueue(
        queue_path,
        stale_seconds=float(stale) if stale is not None else None,
    )

    if args.command == "status":
        import sqlite3
        import time

        conn = sqlite3.connect(queue_path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT job_id, status, created_at, started_at, finished_at
            FROM jobs
            WHERE status IN ('queued', 'running')
            ORDER BY created_at ASC
            """).fetchall()
        now = time.time()
        print(
            json.dumps(
                {
                    "stats": queue.stats(),
                    "active": [
                        {
                            **dict(r),
                            "age_seconds": round(
                                now - float(r["started_at"] or r["created_at"]), 1
                            ),
                        }
                        for r in rows
                    ],
                },
                indent=2,
            )
        )
        return 0

    if args.command == "release":
        released = queue.release_stale_running(
            stale_seconds=args.stale_seconds,
            job_id=args.job_id,
            force=args.force,
        )
        print(json.dumps({"released": released, "stats": queue.stats()}, indent=2))
        return 0

    if args.command == "release-locks":
        cleared: list[str] = []
        repo_lock_name = str(
            ((cfg.get("repos") or {}).get("novelguard") or {}).get("lock_name") or "NovelGuard.lock"
        )
        for path in [locks_dir / repo_lock_name, locks_dir / "automation-worker.lock"]:
            if not path.is_file():
                continue
            if args.force or path.name == "automation-worker.lock":
                alive, _ = (
                    lock_holder_alive(locks_dir)
                    if path.name == "automation-worker.lock"
                    else (False, None)
                )
                if args.force or not alive:
                    if path.name == "automation-worker.lock":
                        clear_lock(locks_dir)
                    else:
                        path.unlink(missing_ok=True)
                    cleared.append(path.name)
            elif clear_stale_file_lock(path):
                cleared.append(path.name)
        print(json.dumps({"cleared": cleared}, indent=2))
        return 0

    if args.command == "reset":
        deleted = queue.reset_job(args.job_id)
        print(
            json.dumps(
                {"job_id": args.job_id, "deleted": deleted, "stats": queue.stats()}, indent=2
            )
        )
        return 0 if deleted else 1

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
