#!/usr/bin/env python3
"""Rich live tail for NovelGuard automation logs.

Usage:
  python scripts/automation_log_watch.py
  python scripts/automation_log_watch.py --file automation/logs/job-xxx.log
  python scripts/automation_log_watch.py --pattern "prompt-*.md"
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Rich live automation log viewer")
    parser.add_argument(
        "--file",
        type=Path,
        help="Log file to follow (default: newest job-*.log)",
    )
    parser.add_argument(
        "--pattern",
        default="job-*.log",
        help="Glob under automation/logs when following latest (default: job-*.log)",
    )
    parser.add_argument(
        "--lines",
        type=int,
        default=40,
        help="Max lines shown in panel (default: 40)",
    )
    parser.add_argument(
        "--hz",
        type=float,
        default=4.0,
        help="Refresh rate (default: 4)",
    )
    args = parser.parse_args(argv)

    from automation.runners.log_watch import logs_dir, newest_log, run_live_watch
    from automation.runners.tui_dashboard import ensure_rich_available

    try:
        ensure_rich_available()
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if args.file:
        path = args.file if args.file.is_absolute() else ROOT / args.file
        if not path.is_file():
            print(f"Log not found: {path}", file=sys.stderr)
            return 1
        pick_latest = False
    else:
        path = newest_log(args.pattern) or logs_dir() / "missing.log"
        pick_latest = True
        if not path.is_file():
            print(
                f"No logs matching {args.pattern!r} in {logs_dir()} — waiting for new files…",
                file=sys.stderr,
            )

    return run_live_watch(
        path,
        refresh_hz=args.hz,
        max_display=args.lines,
        pick_latest=pick_latest,
        glob_pattern=args.pattern,
    )


if __name__ == "__main__":
    raise SystemExit(main())
