#!/usr/bin/env python3
"""Linear webhook → NovelGuard automation queue.

Usage:
  python scripts/linear_webhook_handler.py serve
  python scripts/linear_webhook_handler.py test --fixture automation/examples/linear-webhook-issue-update.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root))

    parser = argparse.ArgumentParser(description="Linear webhook handler for NovelGuard automation")
    sub = parser.add_subparsers(dest="command", required=True)

    serve_p = sub.add_parser("serve", help="Run HTTP webhook receiver")
    serve_p.add_argument("--host", default="")
    serve_p.add_argument("--port", type=int, default=0)

    test_p = sub.add_parser("test", help="Process a fixture JSON (no HTTP)")
    test_p.add_argument("--fixture", type=Path, required=True)

    args = parser.parse_args(argv)

    if args.command == "serve":
        from automation.linear.webhook_server import serve

        host = args.host or None
        port = args.port or None
        if host or port:
            from automation.runners.config import load_config

            cfg = load_config()
            linear = cfg.setdefault("linear", {})
            if args.host:
                linear["webhook_host"] = args.host
            if args.port:
                linear["webhook_port"] = args.port
            host = str(linear.get("webhook_host") or "127.0.0.1")
            port = int(linear.get("webhook_port") or 8765)
            serve(host=host, port=port)
        else:
            serve()
        return 0

    if args.command == "test":
        from automation.linear.webhook import process_linear_webhook

        payload = json.loads(args.fixture.read_text(encoding="utf-8"))
        result = process_linear_webhook(payload)
        print(
            json.dumps(
                {
                    "status": result.status,
                    "message": result.message,
                    "job_id": result.job_id,
                    "queue_depth": result.queue_depth,
                    "active_jobs": result.active_jobs,
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return 0 if result.status in ("queued", "ignored", "deduped") else 1

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
