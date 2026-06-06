"""Invoke Cursor CLI (cursor-agent / agent) with a prompt."""

from __future__ import annotations

import shutil
import subprocess
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import IO, Any, TextIO

from automation.runners.git_guard import prepend_git_guard_path

PROMPT_DELIVERY = "subprocess-stdin"

_active_proc: subprocess.Popen[str] | None = None
_cancel_requested = False
_proc_lock = threading.Lock()


@dataclass(frozen=True)
class CursorRunResult:
    command: list[str]
    returncode: int
    stdout: str
    stderr: str
    dry_run: bool
    stdin_path: str | None = None
    interrupted: bool = False


def resolve_cli(cfg: dict[str, Any]) -> list[str]:
    cursor_cfg = cfg.get("cursor") or {}
    candidates = cursor_cfg.get("commands") or ["cursor-agent", "agent", "cursor"]
    for name in candidates:
        path = shutil.which(str(name))
        if path:
            return [path]
    raise FileNotFoundError(
        f"No Cursor CLI on PATH. Tried: {candidates}. Install: https://cursor.com/cli"
    )


def request_cancel() -> None:
    global _cancel_requested
    with _proc_lock:
        _cancel_requested = True
        proc = _active_proc
    if proc is None:
        return
    try:
        proc.terminate()
    except OSError:
        pass
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        try:
            proc.kill()
        except OSError:
            pass


def is_cursor_proc_running() -> bool:
    with _proc_lock:
        proc = _active_proc
    return proc is not None and proc.poll() is None


def get_cursor_pid() -> int | None:
    with _proc_lock:
        proc = _active_proc
    if proc is None or proc.poll() is not None:
        return None
    return proc.pid


def _logs_dir(cfg: dict[str, Any]) -> Path:
    logs_dir = Path(cfg.get("logs", {}).get("dir", "automation/logs"))
    if not logs_dir.is_absolute():
        from automation.runners.config import repo_root

        logs_dir = repo_root() / logs_dir
    logs_dir.mkdir(parents=True, exist_ok=True)
    return logs_dir


def _append_log_line(log_file: TextIO | None, raw: str) -> None:
    if log_file is None or log_file.closed:
        return
    try:
        log_file.write(raw if raw.endswith("\n") else raw + "\n")
        log_file.flush()
    except (OSError, ValueError):
        # Parent may close the log during interrupt shutdown while readers drain.
        pass


def _read_stream(
    stream: IO[str] | None,
    stream_name: str,
    on_line: Callable[[str, str], None],
    lines: list[str],
    log_file: TextIO | None,
) -> None:
    if stream is None:
        return
    try:
        for raw in iter(stream.readline, ""):
            line = raw.rstrip("\n\r")
            lines.append(raw if raw.endswith("\n") else raw + "\n")
            on_line(stream_name, line)
            _append_log_line(log_file, raw)
    finally:
        stream.close()


def _write_stdin(proc: subprocess.Popen[str], prompt: str) -> None:
    try:
        if proc.stdin is not None:
            proc.stdin.write(prompt)
            proc.stdin.close()
    except OSError:
        pass


def run_prompt_streaming(
    repo: Path,
    prompt: str,
    cfg: dict[str, Any],
    *,
    on_line: Callable[[str, str], None],
    cancel_event: threading.Event | None = None,
    log_file: TextIO | None = None,
) -> CursorRunResult:
    global _active_proc, _cancel_requested

    with _proc_lock:
        _cancel_requested = False

    cursor_cfg = cfg.get("cursor") or {}
    if cursor_cfg.get("dry_run"):
        dry_stdout = "[dry_run] Cursor CLI skipped\n" + prompt[:2000]
        on_line("stdout", "[dry_run] Cursor CLI skipped")
        on_line("stdout", prompt[:2000])
        if log_file is not None:
            log_file.write(dry_stdout)
            log_file.flush()
        return CursorRunResult(
            command=["dry-run"],
            returncode=0,
            stdout=dry_stdout,
            stderr="",
            dry_run=True,
            interrupted=False,
        )

    base = resolve_cli(cfg)
    extra = [str(x) for x in (cursor_cfg.get("args") or ["-p", "--trust", "--force"])]
    cmd = base + extra

    logs_dir = _logs_dir(cfg)
    stdin_path = logs_dir / f"_stdin-{int(time.time())}.md"
    stdin_path.write_text(prompt, encoding="utf-8")
    display_cmd = cmd + [f"<stdin:{stdin_path.name}>"]

    if log_file is not None:
        log_file.write(f"delivery: {PROMPT_DELIVERY}\n")
        log_file.write(f"command: {display_cmd}\n")
        log_file.write(f"stdin_file: {stdin_path}\n")
        log_file.flush()

    proc = subprocess.Popen(
        cmd,
        cwd=repo,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=prepend_git_guard_path(),
    )

    with _proc_lock:
        _active_proc = proc

    stdin_thread = threading.Thread(target=_write_stdin, args=(proc, prompt), daemon=True)
    stdin_thread.start()

    stdout_lines: list[str] = []
    stderr_lines: list[str] = []
    stdout_thread = threading.Thread(
        target=_read_stream,
        args=(proc.stdout, "stdout", on_line, stdout_lines, log_file),
        daemon=True,
    )
    stderr_thread = threading.Thread(
        target=_read_stream,
        args=(proc.stderr, "stderr", on_line, stderr_lines, log_file),
        daemon=True,
    )
    stdout_thread.start()
    stderr_thread.start()

    interrupted = False
    returncode: int | None = None

    try:
        while returncode is None:
            if cancel_event is not None and cancel_event.is_set():
                interrupted = True
                request_cancel()
            with _proc_lock:
                if _cancel_requested:
                    interrupted = True

            returncode = proc.poll()
            if returncode is not None:
                break
            time.sleep(0.1)

        if returncode is None:
            returncode = proc.wait()
    finally:
        if proc.poll() is None:
            try:
                proc.terminate()
            except OSError:
                pass
        stdout_thread.join(timeout=30)
        stderr_thread.join(timeout=30)
        stdin_thread.join(timeout=5)
        with _proc_lock:
            _active_proc = None

    if interrupted and returncode == 0:
        returncode = -1

    _append_log_line(log_file, f"returncode: {returncode}\n")

    return CursorRunResult(
        command=display_cmd,
        returncode=returncode,
        stdout="".join(stdout_lines),
        stderr="".join(stderr_lines),
        dry_run=False,
        stdin_path=str(stdin_path),
        interrupted=interrupted,
    )


def run_prompt(
    repo: Path,
    prompt: str,
    cfg: dict[str, Any],
) -> CursorRunResult:
    cursor_cfg = cfg.get("cursor") or {}
    if cursor_cfg.get("dry_run"):
        return CursorRunResult(
            command=["dry-run"],
            returncode=0,
            stdout="[dry_run] Cursor CLI skipped\n" + prompt[:2000],
            stderr="",
            dry_run=True,
        )

    base = resolve_cli(cfg)
    extra = [str(x) for x in (cursor_cfg.get("args") or ["-p", "--trust", "--force"])]
    cmd = base + extra

    logs_dir = _logs_dir(cfg)
    stdin_path = logs_dir / f"_stdin-{int(time.time())}.md"
    stdin_path.write_text(prompt, encoding="utf-8")

    proc = subprocess.run(
        cmd,
        cwd=repo,
        input=prompt,
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        env=prepend_git_guard_path(),
    )
    display_cmd = cmd + [f"<stdin:{stdin_path.name}>"]

    return CursorRunResult(
        command=display_cmd,
        returncode=proc.returncode,
        stdout=proc.stdout or "",
        stderr=proc.stderr or "",
        dry_run=False,
        stdin_path=str(stdin_path),
    )
