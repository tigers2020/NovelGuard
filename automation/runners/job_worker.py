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
from automation.runners.cursor_runner import run_prompt
from automation.runners.queue import JobQueue, JobRecord

_REQUIRED_PAYLOAD_KEYS = ("id", "repo", "kind", "task")
_VALID_KINDS = frozenset({"implement", "review", "test_fix"})


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


def render_prompt(cfg: dict[str, Any], payload: dict[str, Any], branch: str) -> str:
    prompts_dir = Path(cfg.get("prompts", {}).get("dir", "automation/prompts"))
    if not prompts_dir.is_absolute():
        prompts_dir = repo_root() / prompts_dir
    template_path = prompts_dir / f"{payload['kind']}.md"
    template = template_path.read_text(encoding="utf-8")
    return (
        template.replace("{{TASK}}", str(payload["task"]))
        .replace("{{JOB_ID}}", str(payload["id"]))
        .replace("{{BRANCH}}", branch)
    )


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

    if not repos_cfg.get("use_current_branch_as_base"):
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


def process_job(cfg: dict[str, Any], record: JobRecord) -> dict[str, Any]:
    payload = record.payload
    validate_payload(payload)

    repo_key = str(payload["repo"])
    repo = repo_path(cfg, repo_key)
    repos_cfg = (cfg.get("repos") or {}).get(repo_key) or {}
    lock_name = str(repos_cfg.get("lock_name") or f"{repo_key}.lock")
    locks_dir = Path(cfg.get("locks", {}).get("dir", "automation/locks"))
    if not locks_dir.is_absolute():
        locks_dir = repo_root() / locks_dir
    lock_path = locks_dir / lock_name

    logs_dir = Path(cfg.get("logs", {}).get("dir", "automation/logs"))
    if not logs_dir.is_absolute():
        logs_dir = repo_root() / logs_dir
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_path = logs_dir / f"job-{payload['id']}-{int(time.time())}.log"

    result: dict[str, Any] = {"job_id": payload["id"], "repo": repo_key, "repo_path": str(repo)}

    prefix = str(payload.get("branch_prefix") or "ai/job-")
    planned_branch = f"{prefix}{payload['id']}"
    # Load templates before git checkout (main may not contain automation/ yet).
    prompt = render_prompt(cfg, payload, planned_branch)

    with repo_lock(lock_path):
        branch = prepare_branch(repo, payload, cfg, repo_key)
        result["branch"] = branch

        cursor = run_prompt(repo, prompt, cfg)
        log_path.write_text(
            f"command: {cursor.command}\n"
            f"returncode: {cursor.returncode}\n\n"
            f"--- stdout ---\n{cursor.stdout}\n\n"
            f"--- stderr ---\n{cursor.stderr}\n",
            encoding="utf-8",
        )
        result["cursor"] = {
            "command": cursor.command,
            "returncode": cursor.returncode,
            "dry_run": cursor.dry_run,
            "log_path": str(log_path),
        }

        diff_stat = _git(repo, "diff", "--stat", check=False)
        result["diff_stat"] = diff_stat.stdout or ""

        result["verify"] = run_verify(cfg, payload, repo)
        result["verify_ok"] = all(v["returncode"] == 0 for v in result["verify"])

        ok = cursor.returncode == 0 and result["verify_ok"]
        result["status"] = "succeeded" if ok else "failed"

    result["log_path"] = str(log_path)
    return result


def run_once(cfg: dict[str, Any]) -> bool:
    queue_path = Path(cfg.get("queue", {}).get("path", "automation/jobs/queue.sqlite"))
    if not queue_path.is_absolute():
        queue_path = repo_root() / queue_path

    queue = JobQueue(queue_path)
    record = queue.claim_next()
    if record is None:
        print("No queued jobs.")
        return False

    try:
        result = process_job(cfg, record)
        status = "succeeded" if result.get("status") == "succeeded" else "failed"
        queue.complete(
            record.row_id,
            status=status,
            result=result,
            log_path=result.get("log_path"),
        )
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return status == "succeeded"
    except Exception as exc:
        err = {"status": "failed", "error": str(exc), "job_id": record.payload.get("id")}
        queue.complete(record.row_id, status="failed", result=err)
        print(json.dumps(err, indent=2), file=sys.stderr)
        return False


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
    args = parser.parse_args(argv)

    cfg = load_config()
    if args.once:
        return 0 if run_once(cfg) else 1

    while True:
        had = run_once(cfg)
        if not had:
            time.sleep(args.poll)


if __name__ == "__main__":
    raise SystemExit(main())
