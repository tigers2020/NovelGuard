"""Enqueue an automation job (Hermes / CLI / manual)."""

from __future__ import annotations

import argparse
import json
import time
import uuid
from pathlib import Path
from typing import Any

from automation.runners.config import load_config, repo_root
from automation.runners.queue import JobQueue

_VALID_KINDS = ("implement", "review", "test_fix")


def load_payload_file(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Payload file must be a JSON object: {path}")
    if data.get("merge_approved"):
        raise ValueError("merge_approved must not be set")
    missing = [k for k in ("id", "repo", "kind", "task") if k not in data]
    if missing:
        raise ValueError(f"Payload missing keys: {missing}")
    if data["kind"] not in _VALID_KINDS:
        raise ValueError(f"Invalid kind: {data['kind']!r}")
    return data


def build_payload(args: argparse.Namespace) -> dict[str, Any]:
    job_id = args.id or f"{int(time.time())}-{uuid.uuid4().hex[:8]}"
    payload: dict[str, Any] = {
        "id": job_id,
        "repo": args.repo,
        "kind": args.kind,
        "task": args.task,
        "commit": args.commit,
        "merge_approved": False,
        "safety_level": args.safety_level,
        "verify": args.verify,
        "source": args.source or "cli:enqueue_job",
    }
    if args.base_branch:
        payload["base_branch"] = args.base_branch
    if args.meta_json:
        payload["meta"] = json.loads(args.meta_json)
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Enqueue a NovelGuard automation job")
    parser.add_argument(
        "--payload-file",
        type=Path,
        help="Hermes JSON file (see automation/examples/hermes-job.json)",
    )
    parser.add_argument("--repo", default="novelguard", help="Config repos key")
    parser.add_argument("--kind", choices=_VALID_KINDS)
    parser.add_argument("--task", help="Task text or path to file with task body")
    parser.add_argument("--id", help="Job id (default: timestamp-uuid)")
    parser.add_argument("--commit", action="store_true", help="Allow agent to commit")
    parser.add_argument("--safety-level", type=int, default=2, choices=(1, 2, 3, 4))
    parser.add_argument(
        "--verify",
        default="minimal",
        choices=("none", "minimal", "full", "custom"),
    )
    parser.add_argument("--base-branch", default="")
    parser.add_argument("--source", default="", help="e.g. telegram:cursor-dev")
    parser.add_argument("--meta-json", default="", help='JSON object, e.g. {"chat_id":123}')
    parser.add_argument("--stdin-task", action="store_true", help="Read --task path as file")
    args = parser.parse_args(argv)

    if args.payload_file:
        payload = load_payload_file(args.payload_file)
    else:
        if not args.kind or not args.task:
            parser.error("--kind and --task required unless --payload-file is set")
        task = args.task
        if args.stdin_task or Path(task).is_file():
            task = Path(task).read_text(encoding="utf-8").strip()
        args.task = task
        payload = build_payload(args)

    cfg = load_config()
    queue_path = Path(cfg.get("queue", {}).get("path", "automation/jobs/queue.sqlite"))
    if not queue_path.is_absolute():
        queue_path = repo_root() / queue_path

    queue = JobQueue(queue_path)
    queue.enqueue(payload)
    print(json.dumps({"enqueued": payload["id"], "payload": payload}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
