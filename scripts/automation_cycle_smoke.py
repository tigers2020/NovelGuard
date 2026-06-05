#!/usr/bin/env python3
"""B-depth automation cycle smoke: route → payload → render_prompt."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from automation.runners.cycle_smoke import run_manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Automation cycle smoke (prompt pipeline)")
    parser.add_argument("--group", help="Run only one manifest group id")
    parser.add_argument("--live-compressor", action="store_true", help="Use real Ollama")
    parser.add_argument("--all", action="store_true", help="Run all cases even after failures")
    args = parser.parse_args()

    results = run_manifest(
        group=args.group,
        live_compressor=args.live_compressor,
        stop_on_fail=not args.all,
    )
    for r in results:
        status = "PASS" if r.ok else "FAIL"
        line = f"[{status}] {r.group_id}/{r.case_id}"
        if r.prompt_file:
            line += f" → {r.prompt_file}"
        print(line)
        for err in r.errors:
            print(f"  ! {err}", file=sys.stderr)

    summary = {
        "passed": sum(1 for r in results if r.ok),
        "failed": sum(1 for r in results if not r.ok),
        "total": len(results),
    }
    print(json.dumps(summary, indent=2))
    if summary["failed"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
