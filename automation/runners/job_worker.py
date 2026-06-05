"""Process queued automation jobs: branch → Cursor CLI → verify → result."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from automation.runners.config import load_config, repo_path, repo_root
from automation.runners.cursor_runner import PROMPT_DELIVERY, run_prompt
from automation.runners.queue import JobQueue, JobRecord
from automation.runners.worker_lock import (
    clear_lock,
    clear_stale_file_lock,
    daemon_running,
    write_lock,
)

_REQUIRED_PAYLOAD_KEYS = ("id", "repo", "kind", "task")
_VALID_KINDS = frozenset({"implement", "review", "test_fix", "linear"})


def _git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        text=True,
        capture_output=True,
        check=check,
        encoding="utf-8",
        errors="replace",
    )


@contextmanager
def repo_lock(lock_path: Path) -> Iterator[None]:
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    clear_stale_file_lock(lock_path)
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    try:
        fd = os.open(str(lock_path), flags)
    except FileExistsError as exc:
        raise RuntimeError(f"Repo busy (lock exists): {lock_path}") from exc
    try:
        os.write(fd, f"pid={os.getpid()} ts={time.time()}\n".encode())
        yield
    finally:
        os.close(fd)
        lock_path.unlink(missing_ok=True)


def validate_payload(payload: dict[str, Any]) -> None:
    missing = [k for k in _REQUIRED_PAYLOAD_KEYS if k not in payload]
    if missing:
        raise ValueError(f"Payload missing keys: {missing}")
    if payload["kind"] not in _VALID_KINDS:
        raise ValueError(f"Invalid kind: {payload['kind']!r}")
    if payload.get("merge_approved"):
        raise ValueError("merge_approved must not be set for NovelGuard jobs")
    if payload["kind"] == "linear" and not payload.get("prompt_file"):
        raise ValueError("linear jobs require prompt_file")


def _prompts_dir(cfg: dict[str, Any]) -> Path:
    prompts_dir = Path(cfg.get("prompts", {}).get("dir", "automation/prompts"))
    if not prompts_dir.is_absolute():
        prompts_dir = repo_root() / prompts_dir
    return prompts_dir


def render_prompt(cfg: dict[str, Any], payload: dict[str, Any], branch: str) -> str:
    prompts_dir = _prompts_dir(cfg)
    if payload.get("prompt_file"):
        template_path = prompts_dir / str(payload["prompt_file"])
    else:
        template_path = prompts_dir / f"{payload['kind']}.md"
    if not template_path.is_file():
        raise FileNotFoundError(template_path)

    template = template_path.read_text(encoding="utf-8")
    replacements = {
        "{{TASK}}": str(payload["task"]),
        "{{JOB_ID}}": str(payload["id"]),
        "{{BRANCH}}": branch,
        "{{ISSUE_IDENTIFIER}}": str(payload.get("issue_identifier") or ""),
        "{{ISSUE_URL}}": str(payload.get("issue_url") or ""),
    }
    rendered = template
    for key, value in replacements.items():
        rendered = rendered.replace(key, value)
    return rendered


def _working_tree_dirty(repo: Path) -> bool:
    status = _git(repo, "status", "--porcelain", check=False)
    return bool((status.stdout or "").strip())


def prepare_branch(
    repo: Path,
    payload: dict[str, Any],
    cfg: dict[str, Any],
    repo_key: str,
) -> str:
    if _working_tree_dirty(repo):
        raise RuntimeError(
            "Working tree dirty — commit or stash before automation job "
            "(runner refuses to checkout main over WIP)"
        )

    repos_cfg = (cfg.get("repos") or {}).get(repo_key) or {}
    prefix = str(payload.get("branch_prefix") or "ai/job-")
    branch = f"{prefix}{payload['id']}"

    _git(repo, "fetch", check=False)

    if repos_cfg.get("use_current_branch_as_base"):
        current = _git(repo, "branch", "--show-current", check=True)
        base = (current.stdout or "main").strip()
    else:
        base = str(payload.get("base_branch") or repos_cfg.get("default_branch") or "main")
        _git(repo, "checkout", base)
        _git(repo, "pull", "--ff-only", check=False)
    exists = _git(repo, "rev-parse", "--verify", branch, check=False)
    if exists.returncode == 0:
        _git(repo, "checkout", branch)
    else:
        _git(repo, "checkout", "-b", branch)
    return branch


def _command_lists(cfg: dict[str, Any], payload: dict[str, Any], repo: Path) -> list[list[str]]:
    verify_mode = str(payload.get("verify") or "minimal")
    if verify_mode == "none":
        return []
    if verify_mode == "custom":
        raw = payload.get("verify_commands") or []
        return [[str(x) for x in row] for row in raw]
    verify_cfg = cfg.get("verify") or {}
    if verify_mode == "full":
        return [list(row) for row in (verify_cfg.get("full") or [])]

    commands = [list(row) for row in (verify_cfg.get("minimal") or [])]
    diff = _git(repo, "diff", "--name-only", "HEAD", check=False)
    names = (diff.stdout or "") + (_git(repo, "diff", "--name-only", check=False).stdout or "")
    web_dir = str(verify_cfg.get("web_dir") or "web")
    if any(n.startswith(f"{web_dir}/") for n in names.splitlines()):
        web_extra = verify_cfg.get("web_extra") or []
        commands.extend(list(row) for row in web_extra)
    return commands


def run_verify(
    cfg: dict[str, Any],
    payload: dict[str, Any],
    repo: Path,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for cmd in _command_lists(cfg, payload, repo):
        proc = subprocess.run(
            cmd,
            cwd=repo,
            text=True,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
        )
        results.append(
            {
                "command": cmd,
                "returncode": proc.returncode,
                "stdout_tail": (proc.stdout or "")[-4000:],
                "stderr_tail": (proc.stderr or "")[-4000:],
            }
        )
    return results


def _locks_dir(cfg: dict[str, Any]) -> Path:
    locks_dir = Path(cfg.get("locks", {}).get("dir", "automation/locks"))
    if not locks_dir.is_absolute():
        locks_dir = repo_root() / locks_dir
    return locks_dir


def _logs_dir(cfg: dict[str, Any]) -> Path:
    logs_dir = Path(cfg.get("logs", {}).get("dir", "automation/logs"))
    if not logs_dir.is_absolute():
        logs_dir = repo_root() / logs_dir
    logs_dir.mkdir(parents=True, exist_ok=True)
    return logs_dir


def process_job(cfg: dict[str, Any], record: JobRecord, *, prompt: str) -> dict[str, Any]:
    payload = record.payload
    validate_payload(payload)

    repo_key = str(payload["repo"])
    repo = repo_path(cfg, repo_key)
    repos_cfg = (cfg.get("repos") or {}).get(repo_key) or {}
    lock_name = str(repos_cfg.get("lock_name") or f"{repo_key}.lock")
    locks_dir = _locks_dir(cfg)
    lock_path = locks_dir / lock_name
    logs_dir = _logs_dir(cfg)
    log_path = logs_dir / f"job-{payload['id']}-{int(time.time())}.log"
    prompt_log = logs_dir / f"prompt-{int(time.time())}.md"
    prompt_log.write_text(prompt, encoding="utf-8")

    result: dict[str, Any] = {
        "job_id": payload["id"],
        "repo": repo_key,
        "repo_path": str(repo),
        "prompt_log": str(prompt_log),
    }

    prefix = str(payload.get("branch_prefix") or "ai/job-")
    planned_branch = f"{prefix}{payload['id']}"
    git_prepare = payload.get("git_prepare")
    if git_prepare is None:
        git_prepare = payload["kind"] != "linear"

    with repo_lock(lock_path):
        branch = planned_branch
        if git_prepare:
            branch = prepare_branch(repo, payload, cfg, repo_key)
        result["branch"] = branch

        cursor = run_prompt(repo, prompt, cfg)
        log_path.write_text(
            f"delivery: {PROMPT_DELIVERY}\n"
            f"command: {cursor.command}\n"
            f"stdin_file: {cursor.stdin_path or prompt_log}\n"
            f"returncode: {cursor.returncode}\n"
            f"prompt_log: {prompt_log}\n\n"
            f"--- stdout ---\n{cursor.stdout}\n\n"
            f"--- stderr ---\n{cursor.stderr}\n",
            encoding="utf-8",
        )
        result["cursor"] = {
            "command": cursor.command,
            "returncode": cursor.returncode,
            "dry_run": cursor.dry_run,
            "delivery": PROMPT_DELIVERY,
            "stdin_path": cursor.stdin_path,
            "log_path": str(log_path),
        }

        if git_prepare:
            diff_stat = _git(repo, "diff", "--stat", check=False)
            result["diff_stat"] = diff_stat.stdout or ""

        result["verify"] = run_verify(cfg, payload, repo)
        result["verify_ok"] = all(v["returncode"] == 0 for v in result["verify"])

        ok = cursor.returncode == 0 and result["verify_ok"]
        result["status"] = "succeeded" if ok else "failed"

    result["log_path"] = str(log_path)
    return result


def _queue(cfg: dict[str, Any]) -> JobQueue:
    queue_path = Path(cfg.get("queue", {}).get("path", "automation/jobs/queue.sqlite"))
    if not queue_path.is_absolute():
        queue_path = repo_root() / queue_path
    stale = cfg.get("queue", {}).get("stale_seconds")
    return JobQueue(queue_path, stale_seconds=float(stale) if stale is not None else None)


def run_once(cfg: dict[str, Any], *, quiet_idle: bool = False) -> bool:
    queue = _queue(cfg)
    locks_dir = _locks_dir(cfg)
    queue.recover_orphaned_running(locks_dir)

    record = queue.claim_next()
    if record is None:
        if not quiet_idle:
            print("No queued jobs.")
        return False

    job_id = str(record.payload.get("id") or "")
    prompt_file = record.payload.get("prompt_file") or record.payload.get("kind")
    print(f"[worker] claimed job {job_id} ({prompt_file})", flush=True)

    prefix = str(record.payload.get("branch_prefix") or "ai/job-")
    planned_branch = f"{prefix}{record.payload['id']}"
    prompt = render_prompt(cfg, record.payload, planned_branch)

    write_lock(locks_dir, row_id=record.row_id, job_id=job_id)
    try:
        print(
            "[worker] running cursor-agent — may take several minutes; Ctrl+C requeues job",
            flush=True,
        )
        result = process_job(cfg, record, prompt=prompt)
        status = "succeeded" if result.get("status") == "succeeded" else "failed"
        queue.complete(
            record.row_id,
            status=status,
            result=result,
            log_path=result.get("log_path"),
        )
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return status == "succeeded"
    except KeyboardInterrupt:
        queue.requeue_row(record.row_id)
        print(f"[worker] interrupted — requeued {job_id}", flush=True)
        raise
    except Exception as exc:
        err = {"status": "failed", "error": str(exc), "job_id": job_id}
        queue.complete(record.row_id, status="failed", result=err)
        print(json.dumps(err, indent=2), file=sys.stderr)
        return False
    finally:
        clear_lock(locks_dir)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="NovelGuard automation job worker")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Process a single queued job and exit",
    )
    parser.add_argument(
        "--poll",
        type=float,
        default=15.0,
        help="Seconds between polls when not using --once",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Run even if automation_daemon.py is already active",
    )
    parser.add_argument(
        "--legacy-loop",
        action="store_true",
        help="Poll queue in this process (prefer: scripts/automation_daemon.py)",
    )
    args = parser.parse_args(argv)

    if not args.once and not args.legacy_loop:
        print(
            "[worker] Do not run a poll loop here.\n"
            "  Start automation (webhook + worker):\n"
            "    python scripts/automation_daemon.py\n"
            "  One job only:\n"
            "    python scripts/automation_worker.py --once",
            file=sys.stderr,
        )
        return 2

    cfg = load_config()
    locks_dir = _locks_dir(cfg)
    in_daemon = os.environ.get("NOVELGUARD_AUTOMATION_DAEMON") == "1"
    alive, data = daemon_running(locks_dir)
    if alive and not in_daemon and not args.force:
        pid = int((data or {}).get("pid") or 0)
        print(
            f"[worker] automation daemon already running (pid={pid}). "
            "Use: python scripts/automation_daemon.py",
            file=sys.stderr,
        )
        return 1

    if args.once:
        try:
            return 0 if run_once(cfg) else 1
        except KeyboardInterrupt:
            return 130

    print(
        "[worker] legacy poll loop — prefer: python scripts/automation_daemon.py",
        flush=True,
    )
    while True:
        try:
            had = run_once(cfg)
        except KeyboardInterrupt:
            return 130
        if not had:
            time.sleep(args.poll)


if __name__ == "__main__":
    raise SystemExit(main())
