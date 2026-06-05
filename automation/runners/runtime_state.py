from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Literal

WebhookStatus = Literal["disabled", "starting", "running", "crashed"]
ActiveStage = Literal["idle", "claimed", "git_prepare", "cursor", "verify", "complete"]


@dataclass(frozen=True)
class RuntimeStateSnapshot:
    webhook_enabled: bool
    webhook_status: WebhookStatus
    webhook_host: str
    webhook_port: int
    webhook_path: str
    poll_seconds: float
    started_at: float
    queued: int | None
    running: int | None
    succeeded: int | None
    failed: int | None
    active_job_id: str | None
    active_issue: str | None
    active_stage: str | None
    active_branch: str | None
    log_path: str | None
    active_repo_path: str | None
    cursor_pid: int | None
    cursor_running: bool
    verify_running: bool
    cursor_output_buffered: bool
    git_changed_count: int | None
    git_status_lines: tuple[str, ...]
    job_started_at: float | None
    last_job_status: str | None
    last_job_finished_at: float | None


class RuntimeState:
    def __init__(
        self,
        *,
        webhook_enabled: bool,
        webhook_status: WebhookStatus,
        webhook_host: str,
        webhook_port: int,
        webhook_path: str,
        poll_seconds: float,
        started_at: float,
        queued: int | None = None,
        running: int | None = None,
        succeeded: int | None = None,
        failed: int | None = None,
        active_job_id: str | None = None,
        active_issue: str | None = None,
        active_stage: str | None = "idle",
        active_branch: str | None = None,
        log_path: str | None = None,
        active_repo_path: str | None = None,
        cursor_pid: int | None = None,
        cursor_running: bool = False,
        verify_running: bool = False,
        cursor_output_buffered: bool = False,
        git_changed_count: int | None = None,
        git_status_lines: tuple[str, ...] = (),
        job_started_at: float | None = None,
        last_job_status: str | None = None,
        last_job_finished_at: float | None = None,
    ) -> None:
        self._lock = threading.Lock()
        self.webhook_enabled = webhook_enabled
        self.webhook_status = webhook_status
        self.webhook_host = webhook_host
        self.webhook_port = webhook_port
        self.webhook_path = webhook_path
        self.poll_seconds = poll_seconds
        self.started_at = started_at
        self.queued = queued
        self.running = running
        self.succeeded = succeeded
        self.failed = failed
        self.active_job_id = active_job_id
        self.active_issue = active_issue
        self.active_stage = active_stage
        self.active_branch = active_branch
        self.log_path = log_path
        self.active_repo_path = active_repo_path
        self.cursor_pid = cursor_pid
        self.cursor_running = cursor_running
        self.verify_running = verify_running
        self.cursor_output_buffered = cursor_output_buffered
        self.git_changed_count = git_changed_count
        self.git_status_lines = git_status_lines
        self.job_started_at = job_started_at
        self.last_job_status = last_job_status
        self.last_job_finished_at = last_job_finished_at

    @classmethod
    def initial(
        cls,
        *,
        webhook_enabled: bool,
        host: str,
        port: int,
        path: str,
        poll: float,
        started_at: float | None = None,
    ) -> RuntimeState:
        return cls(
            webhook_enabled=webhook_enabled,
            webhook_status="disabled" if not webhook_enabled else "starting",
            webhook_host=host,
            webhook_port=port,
            webhook_path=path,
            poll_seconds=poll,
            started_at=started_at if started_at is not None else time.time(),
        )

    def snapshot(self) -> RuntimeStateSnapshot:
        with self._lock:
            return RuntimeStateSnapshot(
                webhook_enabled=self.webhook_enabled,
                webhook_status=self.webhook_status,
                webhook_host=self.webhook_host,
                webhook_port=self.webhook_port,
                webhook_path=self.webhook_path,
                poll_seconds=self.poll_seconds,
                started_at=self.started_at,
                queued=self.queued,
                running=self.running,
                succeeded=self.succeeded,
                failed=self.failed,
                active_job_id=self.active_job_id,
                active_issue=self.active_issue,
                active_stage=self.active_stage,
                active_branch=self.active_branch,
                log_path=self.log_path,
                active_repo_path=self.active_repo_path,
                cursor_pid=self.cursor_pid,
                cursor_running=self.cursor_running,
                verify_running=self.verify_running,
                cursor_output_buffered=self.cursor_output_buffered,
                git_changed_count=self.git_changed_count,
                git_status_lines=self.git_status_lines,
                job_started_at=self.job_started_at,
                last_job_status=self.last_job_status,
                last_job_finished_at=self.last_job_finished_at,
            )


_runtime_state: RuntimeState | None = None


def init_runtime_state(
    *,
    webhook_enabled: bool,
    host: str,
    port: int,
    path: str,
    poll: float,
    started_at: float | None = None,
) -> RuntimeState:
    global _runtime_state
    _runtime_state = RuntimeState.initial(
        webhook_enabled=webhook_enabled,
        host=host,
        port=port,
        path=path,
        poll=poll,
        started_at=started_at,
    )
    return _runtime_state


def get_runtime_state() -> RuntimeState:
    if _runtime_state is None:
        raise RuntimeError("runtime state not initialized; call init_runtime_state() first")
    return _runtime_state
