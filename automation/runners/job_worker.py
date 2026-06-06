"""Process queued automation jobs: branch → Cursor CLI → verify → result."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from automation.runners import emit as emit_mod
from automation.runners.config import load_config, repo_path, repo_root
from automation.runners.context_compressor import compress_job_context
from automation.runners.cursor_runner import (
    PROMPT_DELIVERY,
    is_cursor_proc_running,
    request_cancel,
    run_prompt,
    run_prompt_streaming,
)
from automation.runners.cursor_stall import (
    CursorOutputTracker,
    cursor_stall_config,
    diagnose_cursor_stall,
    write_stall_diagnosis,
)
from automation.runners.git_guard import branch_change_error
from automation.runners.queue import JobQueue, JobRecord
from automation.runners.runtime_state import get_runtime_state
from automation.runners.worker_context import get_cancel_event, stop_requested
from automation.runners.worker_lock import (
    clear_lock,
    clear_stale_file_lock,
    daemon_running,
    resolve_locks_dir,
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
    if sys.platform == "win32":
        import msvcrt

        last_exc: OSError | None = None
        for attempt in range(12):
            clear_stale_file_lock(lock_path)
            try:
                handle = open(lock_path, "a+b")
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError as exc:
                last_exc = exc
                if attempt < 11:
                    time.sleep(0.15 * (attempt + 1))
                    continue
                raise RuntimeError(f"Repo busy (lock exists): {lock_path}") from exc
            try:
                handle.seek(0)
                handle.truncate()
                handle.write(f"pid={os.getpid()} ts={time.time()}\n".encode())
                handle.flush()
                yield
            finally:
                try:
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                finally:
                    handle.close()
            return
        if last_exc is not None:
            raise RuntimeError(f"Repo busy (lock exists): {lock_path}") from last_exc
        return

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


# Queued jobs may still reference pre-reorg filenames (see prompts/archive/README.md).
_LEGACY_PROMPT_ALIASES: dict[str, str] = {
    "00-linear-create-pr-to-spec.md": "linear/backlog/create-research.md",
    "01a-linear-spec.md": "linear/todo/write-spec.md",
    "01b-linear-grill-plan.md": "linear/backlog/grill-plan.md",
    "01c-linear-spec-revise.md": "linear/todo/revise-spec.md",
    "01d-linear-todo-list.md": "linear/todo/write-task-list.md",
    "02-linear-in-progress-implement.md": "linear/in-progress/implement.md",
    "03-linear-in-review-verification.md": "linear/in-review/verify.md",
    "linear-issue-created.md": "linear/backlog/create-research.md",
}

_PROMPT_PATH_ALIASES: dict[str, str] = {
    "linear/todo/write-todo-list.md": "linear/todo/write-task-list.md",
}


def _resolve_prompt_file(prompts_dir: Path, prompt_file: str) -> str:
    """Resolve legacy prompt paths to linear/ or archive/ when the direct file is gone."""
    direct = prompts_dir / prompt_file
    if direct.is_file():
        return prompt_file
    path_alias = _PROMPT_PATH_ALIASES.get(prompt_file)
    if path_alias and (prompts_dir / path_alias).is_file():
        return path_alias
    alias = _LEGACY_PROMPT_ALIASES.get(prompt_file)
    if alias and (prompts_dir / alias).is_file():
        return alias
    archived = prompts_dir / "archive" / prompt_file
    if archived.is_file():
        return f"archive/{prompt_file}"
    return prompt_file


def render_prompt(cfg: dict[str, Any], payload: dict[str, Any], branch: str) -> str:
    prompts_dir = _prompts_dir(cfg)
    if payload.get("prompt_file"):
        rel = _resolve_prompt_file(prompts_dir, str(payload["prompt_file"]))
        template_path = prompts_dir / rel
    else:
        template_path = prompts_dir / f"{payload['kind']}.md"
    if not template_path.is_file():
        raise FileNotFoundError(template_path)

    template = template_path.read_text(encoding="utf-8")
    meta = payload.get("meta") if isinstance(payload.get("meta"), dict) else {}
    linear_event = meta.get("linear_event") if isinstance(meta, dict) else None
    raw_context = "\n".join(
        [
            str(payload.get("task") or ""),
            str(meta.get("route_reason") or ""),
            json.dumps(linear_event or {}, ensure_ascii=False),
        ]
    )
    memory_result = compress_job_context(cfg, payload=payload, raw_context=raw_context)
    memory = memory_result.get("memory")
    memory_json = json.dumps(memory, ensure_ascii=False, indent=2) if memory else "{}"
    replacements = {
        "{{TASK}}": str(payload["task"]),
        "{{JOB_ID}}": str(payload["id"]),
        "{{BRANCH}}": branch,
        "{{ISSUE_IDENTIFIER}}": str(payload.get("issue_identifier") or ""),
        "{{ISSUE_URL}}": str(payload.get("issue_url") or ""),
        "{{ROUTE_REASON}}": str(meta.get("route_reason") or ""),
        "{{LINEAR_STATE}}": str(payload.get("linear_state") or ""),
        "{{LINEAR_EVENT}}": json.dumps(
            linear_event or {},
            ensure_ascii=False,
            separators=(",", ":"),
        ),
        "{{CONTEXT_MEMORY_JSON}}": memory_json,
        "{{NEXT_PROMPT}}": str((memory or {}).get("next_prompt") or payload.get("task") or ""),
    }
    rendered = template
    for key, value in replacements.items():
        rendered = rendered.replace(key, value)
    return rendered


def _working_tree_dirty(repo: Path) -> bool:
    status = _git(repo, "status", "--porcelain", check=False)
    return bool((status.stdout or "").strip())


def _current_branch(repo: Path) -> str:
    result = _git(repo, "rev-parse", "--abbrev-ref", "HEAD", check=False)
    if result.returncode != 0:
        return "?"
    return (result.stdout or "").strip()


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


def _runtime_state_or_none():
    try:
        return get_runtime_state()
    except RuntimeError:
        return None


def run_verify(
    cfg: dict[str, Any],
    payload: dict[str, Any],
    repo: Path,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    state = _runtime_state_or_none()
    if state is not None and emit_mod.is_tui_mode():
        state.active_stage = "verify"
        state.verify_running = True

    for cmd in _command_lists(cfg, payload, repo):
        if emit_mod.is_tui_mode():
            emit_mod.emit_or_print("verify", "verify.start", " ".join(cmd))
        proc = subprocess.run(
            cmd,
            cwd=repo,
            text=True,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
        )
        row = {
            "command": cmd,
            "returncode": proc.returncode,
            "stdout_tail": (proc.stdout or "")[-4000:],
            "stderr_tail": (proc.stderr or "")[-4000:],
        }
        results.append(row)
        if emit_mod.is_tui_mode():
            emit_mod.emit_or_print(
                "verify",
                "verify.done",
                f"exit {proc.returncode}: {' '.join(cmd)}",
            )
            if proc.returncode != 0:
                emit_mod.emit_or_print(
                    "verify",
                    "verify.fail",
                    f"exit {proc.returncode}: {' '.join(cmd)}",
                )

    if state is not None and emit_mod.is_tui_mode():
        state.verify_running = False

    return results


def _locks_dir(cfg: dict[str, Any]) -> Path:
    return resolve_locks_dir(cfg)


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
        state = _runtime_state_or_none()
        tui = emit_mod.is_tui_mode()

        if git_prepare:
            if state is not None and tui:
                state.active_stage = "git_prepare"
            branch = prepare_branch(repo, payload, cfg, repo_key)
        result["branch"] = branch

        if state is not None and tui:
            state.active_branch = branch
            state.active_stage = "cursor"
            state.cursor_running = True
            state.log_path = str(log_path)
            state.cursor_output_buffered = False

        agent_branch = _current_branch(repo)
        result["start_branch"] = agent_branch

        if tui:
            stall_seconds, stall_max_retries, stall_poll = cursor_stall_config(cfg)
            stall_retries = 0
            cursor = None

            log_file = log_path.open("w", encoding="utf-8")
            try:
                log_file.write(f"prompt_log: {prompt_log}\n\n")
                log_file.flush()

                for attempt in range(stall_max_retries + 1):
                    tracker = CursorOutputTracker()
                    monitor_stop = threading.Event()
                    stall_cancelled = threading.Event()

                    def on_line(
                        stream: str, line: str, *, _tracker: CursorOutputTracker = tracker
                    ) -> None:
                        _tracker.note_line(stream, line)
                        if state is not None:
                            state.cursor_output_buffered = False
                        emit_mod.emit_or_print("cursor", "cursor.line", line)

                    def _stall_monitor(
                        *,
                        _tracker: CursorOutputTracker = tracker,
                        _attempt: int = attempt,
                    ) -> None:
                        while not monitor_stop.wait(stall_poll):
                            if not is_cursor_proc_running():
                                break
                            idle = _tracker.idle_seconds()
                            if state is not None and idle >= 30.0:
                                state.cursor_output_buffered = True
                            if idle >= stall_seconds and is_cursor_proc_running():
                                diagnosis = diagnose_cursor_stall(
                                    tracker=_tracker,
                                    attempt=_attempt + 1,
                                    log_path=str(log_path),
                                )
                                write_stall_diagnosis(diagnosis, log_file=log_file)
                                request_cancel()
                                stall_cancelled.set()
                                break

                    monitor_thread = threading.Thread(target=_stall_monitor, daemon=True)
                    monitor_thread.start()
                    try:
                        cursor = run_prompt_streaming(
                            repo,
                            prompt,
                            cfg,
                            on_line=on_line,
                            cancel_event=get_cancel_event(),
                            log_file=log_file,
                        )
                    finally:
                        monitor_stop.set()
                        monitor_thread.join(timeout=1.0)

                    if stall_cancelled.is_set() and attempt < stall_max_retries:
                        stall_retries += 1
                        log_file.write(f"\n--- stall retry {stall_retries} ---\n")
                        log_file.flush()
                        continue
                    break

                log_file.write(
                    f"\n--- stdout ---\n{cursor.stdout}\n\n" f"--- stderr ---\n{cursor.stderr}\n"
                )
            finally:
                log_file.close()

            if state is not None:
                state.cursor_running = False
        else:
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
            "interrupted": cursor.interrupted,
        }
        if tui:
            result["cursor"]["stall_retries"] = stall_retries

        end_branch = _current_branch(repo)
        result["end_branch"] = end_branch
        branch_err = branch_change_error(agent_branch, end_branch)
        if branch_err:
            result["branch_guard_failed"] = True
            result["branch_guard_error"] = branch_err
            with log_path.open("a", encoding="utf-8") as log_file:
                log_file.write(f"\n--- branch guard ---\n{branch_err}\n")

        if git_prepare:
            diff_stat = _git(repo, "diff", "--stat", check=False)
            result["diff_stat"] = diff_stat.stdout or ""

        result["verify"] = run_verify(cfg, payload, repo)
        result["verify_ok"] = all(v["returncode"] == 0 for v in result["verify"])

        ok = cursor.returncode == 0 and result["verify_ok"] and branch_err is None
        result["status"] = "succeeded" if ok else "failed"

    result["log_path"] = str(log_path)
    return result


def _queue(cfg: dict[str, Any]) -> JobQueue:
    queue_path = Path(cfg.get("queue", {}).get("path", "automation/jobs/queue.sqlite"))
    if not queue_path.is_absolute():
        queue_path = repo_root() / queue_path
    stale = cfg.get("queue", {}).get("stale_seconds")
    return JobQueue(queue_path, stale_seconds=float(stale) if stale is not None else None)


def run_once(
    cfg: dict[str, Any],
    *,
    quiet_idle: bool = False,
    queue: JobQueue | None = None,
    locks_dir: Path | None = None,
    recover_orphans: bool = True,
) -> bool:
    queue = queue or _queue(cfg)
    locks_dir = locks_dir or _locks_dir(cfg)
    if recover_orphans:
        queue.recover_orphaned_running(locks_dir)

    record = queue.claim_next()
    if record is None:
        if not quiet_idle:
            emit_mod.emit_or_print(
                "worker",
                "idle",
                "No queued jobs.",
                plain_prefix="No queued jobs.",
            )
        return False

    job_id = str(record.payload.get("id") or "")
    prompt_file = record.payload.get("prompt_file") or record.payload.get("kind")
    emit_mod.emit_or_print(
        "worker",
        "claimed",
        f"job {job_id} ({prompt_file})",
        plain_prefix=f"[worker] claimed job {job_id} ({prompt_file})",
    )

    state = _runtime_state_or_none()
    if state is not None and emit_mod.is_tui_mode():
        state.active_job_id = job_id
        state.active_stage = "claimed"
        state.job_started_at = time.time()
        issue_id = str(record.payload.get("issue_identifier") or "").strip()
        if not issue_id:
            match = re.search(r"NOV-\d+", job_id)
            if match:
                issue_id = match.group(0)
        if issue_id:
            state.active_issue = issue_id
        try:
            state.active_repo_path = str(
                repo_path(cfg, str(record.payload.get("repo") or "novelguard"))
            )
        except KeyError:
            pass

    prefix = str(record.payload.get("branch_prefix") or "ai/job-")
    planned_branch = f"{prefix}{record.payload['id']}"

    write_lock(locks_dir, row_id=record.row_id, job_id=job_id)
    try:
        prompt = render_prompt(cfg, record.payload, planned_branch)
        emit_mod.emit_or_print(
            "worker",
            "running",
            "cursor-agent — may take several minutes; Ctrl+C requeues job",
            plain_prefix=(
                "[worker] running cursor-agent — may take several minutes; Ctrl+C requeues job"
            ),
        )
        result = process_job(cfg, record, prompt=prompt)
        status = "succeeded" if result.get("status") == "succeeded" else "failed"
        queue.complete(
            record.row_id,
            status=status,
            result=result,
            log_path=result.get("log_path"),
        )
        if emit_mod.is_tui_mode():
            verify_ok = result.get("verify_ok", False)
            log_path = result.get("log_path", "")
            emit_mod.emit_or_print(
                "worker",
                "worker.complete",
                f"{status} verify_ok={verify_ok} log={log_path}",
            )
            if state is not None:
                state.active_stage = "complete"
                state.last_job_status = status
                state.last_job_finished_at = time.time()
                state.active_job_id = None
        else:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        return status == "succeeded"
    except KeyboardInterrupt:
        if stop_requested() and is_cursor_proc_running():
            from automation.runners.cursor_runner import request_cancel

            request_cancel()
        queue.requeue_row(record.row_id)
        emit_mod.emit_or_print(
            "worker",
            "interrupted",
            f"requeued {job_id}",
            plain_prefix=f"[worker] interrupted — requeued {job_id}",
        )
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
