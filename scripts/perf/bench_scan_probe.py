"""Benchmark scan probe phase for large libraries (local only, not CI).

Usage:
  PYTHONPATH=src python scripts/bench_scan_probe.py [--root PATH] [--runs 3]
"""

from __future__ import annotations

import argparse
import statistics
import time
from pathlib import Path


def _bench_probe(root: Path, *, warmup: int, runs: int) -> list[float]:
    from infrastructure.scan_content_probe import (
        collect_scan_path_entries,
        enrich_scan_entries_with_content_probe,
    )

    allowed = {".txt", ".md"}

    def cancel_check() -> bool:
        return False

    def noop_progress(_pct: int, _label: str) -> None:
        pass

    for _ in range(warmup):
        entries = collect_scan_path_entries(
            root,
            allowed_extensions=allowed,
            include_hidden=False,
            cancel_check=cancel_check,
        )
        records: list[object] = []

        def out(record: object) -> None:
            records.append(record)

        enrich_scan_entries_with_content_probe(
            entries,
            on_progress=noop_progress,
            cancel_check=cancel_check,
            out=out,
        )

    timings: list[float] = []
    for _ in range(runs):
        entries = collect_scan_path_entries(
            root,
            allowed_extensions=allowed,
            include_hidden=False,
            cancel_check=cancel_check,
        )
        records: list[object] = []

        def out(record: object) -> None:
            records.append(record)

        t0 = time.perf_counter()
        enrich_scan_entries_with_content_probe(
            entries,
            on_progress=noop_progress,
            cancel_check=cancel_check,
            out=out,
        )
        probe_ms = (time.perf_counter() - t0) * 1000
        timings.append(probe_ms)
        print(f"  probe={probe_ms:.0f}ms records={len(records)}")

    return timings


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark scan content probe phase")
    parser.add_argument("--root", type=Path, default=Path(".bench_probe_7k"))
    parser.add_argument("--warmup", type=int, default=1)
    parser.add_argument("--runs", type=int, default=3)
    args = parser.parse_args()

    root = args.root.resolve()
    if not root.is_dir():
        print(f"Missing benchmark root: {root}")
        return 1

    actual = sum(1 for _ in root.rglob("*.txt"))
    print(f"bench_scan_probe root={root} actual={actual} runs={args.runs}")
    timings = _bench_probe(root, warmup=args.warmup, runs=args.runs)
    median = statistics.median(timings)
    print(f"PROBE_MEDIAN_MS={median:.1f}")
    print(f"PROBE_SAMPLES_MS={[round(t, 1) for t in timings]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
