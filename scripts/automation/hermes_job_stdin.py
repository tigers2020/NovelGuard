#!/usr/bin/env python3
"""Read one job JSON from stdin and enqueue (Hermes pipe)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    if str(_ROOT) not in sys.path:
        sys.path.insert(0, str(_ROOT))

    from automation.runners.config import load_config, repo_root
    from automation.runners.enqueue_job import load_payload_file
    from automation.runners.queue import JobQueue

    raw = sys.stdin.read()
    if not raw.strip():
        print("FAIL: empty stdin", file=sys.stderr)
        return 2

    data = json.loads(raw)
    tmp = repo_root() / "automation" / "jobs" / "_stdin-payload.json"
    tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    try:
        payload = load_payload_file(tmp)
    finally:
        tmp.unlink(missing_ok=True)

    cfg = load_config()
    queue_path = Path(cfg.get("queue", {}).get("path", "automation/jobs/queue.sqlite"))
    if not queue_path.is_absolute():
        queue_path = repo_root() / queue_path

    JobQueue(queue_path).enqueue(payload)
    print(json.dumps({"enqueued": payload["id"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
