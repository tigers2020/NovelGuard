#!/usr/bin/env python3
"""Enqueue job from Hermes JSON. Usage: python scripts/hermes_enqueue.py automation/examples/hermes-job.json"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python scripts/hermes_enqueue.py <job.json>", file=sys.stderr)
        return 2
    if str(_ROOT) not in sys.path:
        sys.path.insert(0, str(_ROOT))

    from automation.runners.config import load_config, repo_root
    from automation.runners.enqueue_job import load_payload_file
    from automation.runners.queue import JobQueue

    path = Path(sys.argv[1])
    payload = load_payload_file(path)
    cfg = load_config()
    queue_path = Path(cfg.get("queue", {}).get("path", "automation/jobs/queue.sqlite"))
    if not queue_path.is_absolute():
        queue_path = repo_root() / queue_path
    JobQueue(queue_path).enqueue(payload)
    print(json.dumps({"enqueued": payload["id"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
