"""Track whether an automation worker is actively processing a job."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def pid_alive(pid: int) -> bool:
    return _pid_alive(pid)


def parse_pid_lock_file(lock_path: Path) -> int | None:
    try:
        text = lock_path.read_text(encoding="utf-8")
    except OSError:
        return None
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("pid="):
            raw = line.split("=", 1)[1].strip().split()[0]
            try:
                return int(raw)
            except ValueError:
                return None
    return None


def clear_stale_file_lock(lock_path: Path) -> bool:
    """Remove a PID lock file when the holder process is gone."""
    if not lock_path.is_file():
        return False
    pid = parse_pid_lock_file(lock_path)
    if pid is None or not _pid_alive(pid):
        lock_path.unlink(missing_ok=True)
        return True
    return False


def lock_path(locks_dir: Path) -> Path:
    return locks_dir / "automation-worker.lock"


def write_lock(locks_dir: Path, *, row_id: int, job_id: str) -> None:
    locks_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "pid": os.getpid(),
        "row_id": row_id,
        "job_id": job_id,
        "started_at": time.time(),
    }
    lock_path(locks_dir).write_text(json.dumps(payload), encoding="utf-8")


def read_lock(locks_dir: Path) -> dict[str, Any] | None:
    path = lock_path(locks_dir)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    return data if isinstance(data, dict) else None


def clear_lock(locks_dir: Path) -> None:
    path = lock_path(locks_dir)
    if path.is_file():
        path.unlink()


def lock_holder_alive(locks_dir: Path) -> tuple[bool, dict[str, Any] | None]:
    data = read_lock(locks_dir)
    if data is None:
        return False, None
    pid = int(data.get("pid") or 0)
    if _pid_alive(pid):
        return True, data
    return False, data


def daemon_lock_path(locks_dir: Path) -> Path:
    return locks_dir / "automation-daemon.lock"


def read_daemon_lock(locks_dir: Path) -> dict[str, Any] | None:
    path = daemon_lock_path(locks_dir)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    return data if isinstance(data, dict) else None


def daemon_running(locks_dir: Path) -> tuple[bool, dict[str, Any] | None]:
    data = read_daemon_lock(locks_dir)
    if data is None:
        return False, None
    pid = int(data.get("pid") or 0)
    if _pid_alive(pid):
        return True, data
    return False, data


def acquire_daemon_lock(locks_dir: Path) -> None:
    locks_dir.mkdir(parents=True, exist_ok=True)
    path = daemon_lock_path(locks_dir)
    alive, data = daemon_running(locks_dir)
    if alive and data:
        pid = int(data.get("pid") or 0)
        raise RuntimeError(
            f"Automation daemon already running (pid={pid}). " "Stop it before starting another."
        )
    if path.is_file():
        path.unlink(missing_ok=True)
    payload = {"pid": os.getpid(), "started_at": time.time()}
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    try:
        fd = os.open(str(path), flags)
    except FileExistsError as exc:
        raise RuntimeError(f"Automation daemon lock exists: {path}") from exc
    try:
        os.write(fd, json.dumps(payload).encode("utf-8"))
    finally:
        os.close(fd)


def release_daemon_lock(locks_dir: Path) -> None:
    path = daemon_lock_path(locks_dir)
    if not path.is_file():
        return
    data = read_daemon_lock(locks_dir)
    if data and int(data.get("pid") or 0) == os.getpid():
        path.unlink(missing_ok=True)


def release_stale_locks(cfg: dict[str, Any]) -> list[str]:
    """Clear dead PID repo/worker/daemon locks before processing."""
    locks_dir = Path(cfg.get("locks", {}).get("dir", "automation/locks"))
    if not locks_dir.is_absolute():
        from automation.runners.config import repo_root

        locks_dir = repo_root() / locks_dir
    cleared: list[str] = []
    repo_lock_name = str(
        ((cfg.get("repos") or {}).get("novelguard") or {}).get("lock_name") or "NovelGuard.lock"
    )
    for name in (repo_lock_name, "automation-worker.lock"):
        path = locks_dir / name
        if clear_stale_file_lock(path):
            cleared.append(name)
    daemon_path = daemon_lock_path(locks_dir)
    alive, _ = daemon_running(locks_dir)
    if daemon_path.is_file() and not alive:
        daemon_path.unlink(missing_ok=True)
        cleared.append("automation-daemon.lock")
    return cleared
