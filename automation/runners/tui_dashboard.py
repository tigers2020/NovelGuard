from __future__ import annotations

import re
import shutil
import threading
import time
from collections.abc import Callable
from pathlib import Path

from automation.runners.event_bus import Event, EventBus
from automation.runners.log_tail import read_log_tail
from automation.runners.runtime_state import RuntimeState, RuntimeStateSnapshot

NARROW_WIDTH = 120
_LOG_META_PREFIXES = ("prompt_log:", "delivery:", "command:", "stdin_file:")
_ISSUE_RE = re.compile(r"\bNOV-\d+\b")
_STATUS_KV_RE = re.compile(r"status=([^\s]+)")
_ISSUE_KV_RE = re.compile(r"issue=([^\s]+)")
_CLAIMED_JOB_RE = re.compile(r"job\s+(\S+)")
_PROMPT_FILE_RE = re.compile(r"\(([^)]+)\)\s*$")


def ensure_rich_available() -> None:
    try:
        import rich  # noqa: F401
    except ImportError as exc:
        import sys

        py = sys.executable
        raise RuntimeError(
            f"Rich is required for --tui. Install into this Python: "
            f'"{py}" -m pip install -e ".[automation]"'
        ) from exc


def _terminal_width() -> int:
    return shutil.get_terminal_size(fallback=(NARROW_WIDTH, 40)).columns


def _format_duration(seconds: float) -> str:
    total = max(0, int(seconds))
    if total < 60:
        return f"{total:02d}s"
    minutes, secs = divmod(total, 60)
    if minutes < 60:
        return f"{minutes:02d}:{secs:02d}"
    hours, minutes = divmod(minutes, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def _format_count(value: int | None) -> str:
    return "?" if value is None else str(value)


def _truncate(text: str, max_len: int) -> str:
    if len(text) <= max_len:
        return text
    if max_len <= 3:
        return text[:max_len]
    return text[: max_len - 3] + "..."


def _short_path(path: str, max_len: int = 56) -> str:
    if len(path) <= max_len:
        return path
    name = Path(path).name
    if len(name) >= max_len - 4:
        return "..." + _truncate(name, max_len - 3)
    return "..." + name


def _issue_from_text(text: str) -> str:
    m = _ISSUE_KV_RE.search(text)
    if m:
        return m.group(1)
    m = _ISSUE_RE.search(text)
    if m:
        return m.group(0)
    m = _CLAIMED_JOB_RE.search(text)
    if m:
        found = _ISSUE_RE.search(m.group(1))
        if found:
            return found.group(0)
    return "-"


def _short_prompt_name(text: str) -> str:
    m = _PROMPT_FILE_RE.search(text)
    if not m:
        return _truncate(text, 28)
    name = m.group(1)
    if name.endswith(".md"):
        name = name[: -len(".md")]
    if name[:2].isdigit() and name[2:3] == "-":
        name = name[3:]
    return _truncate(name.replace("-", " "), 24)


def format_event_display(event: Event) -> str:
    """Compact one-line event for the dashboard (not raw log)."""
    clock = time.strftime("%H:%M:%S", time.localtime(event.ts))
    source = event.source[:6].ljust(6)
    issue = _issue_from_text(event.summary)
    kind = event.kind

    if kind == "cursor.line":
        return ""

    if kind == "webhook.post":
        status_m = _STATUS_KV_RE.search(event.summary)
        status = status_m.group(1) if status_m else "?"
        msg = event.summary.split("msg=", 1)[-1] if "msg=" in event.summary else ""
        msg = _truncate(msg, 22)
        return f"{clock}  {source}  {issue:<8}  {status:<8}  {_short_prompt_name(msg)}"

    if kind == "worker.claimed":
        stage = _short_prompt_name(event.summary)
        return f"{clock}  {source}  {issue:<8}  claimed   {stage}"

    if kind == "worker.running":
        return f"{clock}  {source}  {issue:<8}  cursor    starting"

    if kind == "worker.complete":
        parts = event.summary.split()
        status = parts[0] if parts else "?"
        return f"{clock}  {source}  {issue:<8}  done      {status}"

    if kind.startswith("verify."):
        verb = kind.split(".", 1)[-1]
        cmd = _truncate(event.summary, 28)
        return f"{clock}  {source}  {issue:<8}  {verb:<8}  {cmd}"

    if kind == "worker.interrupted":
        return f"{clock}  {source}  {issue:<8}  requeue   {_truncate(event.summary, 22)}"

    if kind == "webhook.crashed":
        return f"{clock}  {source}  {'-':<8}  crashed   {_truncate(event.summary, 22)}"

    summary = _truncate(event.summary, 36)
    return f"{clock}  {source}  {issue:<8}  {kind:<8}  {summary}"


def _build_header(snapshot: RuntimeStateSnapshot) -> str:
    uptime = _format_duration(time.time() - snapshot.started_at)
    status = snapshot.webhook_status
    if status == "running":
        webhook = "webhook ok"
    elif status == "disabled":
        webhook = "webhook off"
    else:
        webhook = f"webhook {status}"
    host_port = f"{snapshot.webhook_host}:{snapshot.webhook_port}"
    poll = snapshot.poll_seconds
    poll_text = f"{int(poll)}s" if poll == int(poll) else f"{poll}s"
    line1 = f"{webhook}  {host_port}  poll {poll_text}  uptime {uptime}"
    line2 = (
        f"Queue: queued {_format_count(snapshot.queued)} · "
        f"running {_format_count(snapshot.running)} · "
        f"ok {_format_count(snapshot.succeeded)} · "
        f"fail {_format_count(snapshot.failed)}"
    )
    return f"{line1}\n{line2}"


def _build_current_job_panel(snapshot: RuntimeStateSnapshot) -> str:
    if not (
        snapshot.active_job_id
        or snapshot.active_issue
        or (snapshot.active_stage and snapshot.active_stage not in ("idle", "complete"))
    ):
        return "idle"

    issue = snapshot.active_issue or _issue_from_text(snapshot.active_job_id or "") or "-"
    stage = snapshot.active_stage or "?"
    elapsed = (
        _format_duration(time.time() - snapshot.job_started_at)
        if snapshot.job_started_at is not None
        else "-"
    )
    branch = _truncate(Path(snapshot.active_branch or "-").name, 28)
    log_name = Path(snapshot.log_path).name if snapshot.log_path else "-"

    lines = [
        f"Issue:   {issue}",
        f"Stage:   {stage}",
        f"Elapsed: {elapsed}",
        f"Branch:  {branch}",
        f"Log:     {log_name}",
    ]
    if snapshot.cursor_running:
        lines.append("Agent:   running")
    elif snapshot.verify_running:
        lines.append("Verify:  running")
    elif snapshot.cursor_output_buffered:
        lines.append("Agent:   buffered (tailing log)")
    return "\n".join(lines)


def _build_events_panel(events: list[Event]) -> str:
    rows = [format_event_display(e) for e in events]
    rows = [r for r in rows if r]
    if not rows:
        return "(no events yet)"
    return "\n".join(rows[-30:])


def _basename_branch(branch: str | None) -> str:
    if not branch:
        return "-"
    return Path(branch).name if "/" in branch or "\\" in branch else branch


def _filter_log_content(lines: list[str]) -> list[str]:
    filtered = [ln for ln in lines if ln.strip() and not ln.startswith(_LOG_META_PREFIXES)]
    return filtered if filtered else lines


def _build_git_section(snapshot: RuntimeStateSnapshot) -> list[str]:
    if not (snapshot.cursor_running or snapshot.verify_running):
        return []
    count = snapshot.git_changed_count
    if count is None:
        return []
    if count == 0 and not snapshot.git_status_lines:
        return ["Changed files: (none yet)"]
    header = f"Changed files ({count}):"
    return [header, *list(snapshot.git_status_lines)]


def _build_agent_panel(
    snapshot: RuntimeStateSnapshot,
    cursor_lines: list[str],
    *,
    log_tail: list[str],
    log_age_s: float | None,
) -> str:
    active = snapshot.cursor_running or snapshot.verify_running or snapshot.cursor_output_buffered
    stage_active = bool(
        snapshot.active_stage and snapshot.active_stage not in ("idle", "complete")
    )
    if not active and not cursor_lines and not stage_active:
        return "idle"

    header_parts: list[str] = []
    if snapshot.cursor_running:
        header_parts.append("cursor-agent running")
    elif snapshot.verify_running:
        header_parts.append("verify running")
    elif stage_active:
        header_parts.append(snapshot.active_stage or "preparing")

    if snapshot.job_started_at is not None and (active or stage_active):
        header_parts.append(f"elapsed {_format_duration(time.time() - snapshot.job_started_at)}")

    if log_age_s is not None and snapshot.log_path:
        header_parts.append(f"log updated {int(log_age_s)}s ago")

    if snapshot.cursor_pid:
        header_parts.append(f"pid {snapshot.cursor_pid}")

    if snapshot.active_branch and (active or stage_active):
        header_parts.append(f"branch {_basename_branch(snapshot.active_branch)}")

    lines: list[str] = []
    if header_parts:
        lines.append(" · ".join(header_parts))

    git_section = _build_git_section(snapshot)
    if git_section:
        if lines:
            lines.append("")
        lines.extend(git_section)

    body: list[str] = []
    if cursor_lines:
        body = cursor_lines[-30:]
    elif log_tail:
        body = _filter_log_content(log_tail)[-30:]
    elif snapshot.cursor_running:
        body = ["(waiting for agent output)"]
    elif stage_active:
        body = [f"({snapshot.active_stage or 'preparing'} — waiting for cursor-agent)"]

    if body:
        if lines:
            lines.append("")
        lines.extend(body)

    if snapshot.log_path and active:
        lines.append("")
        lines.append(snapshot.log_path)

    return "\n".join(lines) if lines else "idle"


def _agent_log_tail(snapshot: RuntimeStateSnapshot) -> tuple[list[str], float | None]:
    should_tail = bool(
        snapshot.log_path
        and (snapshot.cursor_output_buffered or snapshot.cursor_running or snapshot.verify_running)
    )
    if not should_tail:
        return [], None
    return read_log_tail(snapshot.log_path, max_lines=40)


def build_layout(
    snapshot: RuntimeStateSnapshot,
    events: list[Event],
    cursor_lines: list[str],
    *,
    terminal_width: int | None = None,
):
    from rich.layout import Layout
    from rich.panel import Panel
    from rich.text import Text

    width = terminal_width if terminal_width is not None else _terminal_width()
    narrow = width < NARROW_WIDTH
    log_tail, log_age = _agent_log_tail(snapshot)

    layout = Layout()
    if narrow:
        layout.split_column(
            Layout(name="header", size=4),
            Layout(name="current", size=6),
            Layout(name="events", ratio=35),
            Layout(name="agent", ratio=55),
        )
    else:
        layout.split_column(
            Layout(name="header", size=4),
            Layout(name="current", size=6),
            Layout(name="body", ratio=1),
        )
        layout["body"].split_row(
            Layout(name="events", ratio=35),
            Layout(name="agent", ratio=55),
        )

    layout["header"].update(
        Panel(
            Text(_build_header(snapshot)),
            title="NovelGuard Automation",
            border_style="bold blue",
        )
    )
    layout["current"].update(
        Panel(
            Text(_build_current_job_panel(snapshot)),
            title="Current Job",
            border_style="magenta",
        )
    )
    layout["events"].update(
        Panel(Text(_build_events_panel(events)), title="Events", border_style="yellow")
    )
    layout["agent"].update(
        Panel(
            Text(
                _build_agent_panel(
                    snapshot,
                    cursor_lines,
                    log_tail=log_tail,
                    log_age_s=log_age,
                )
            ),
            title="Agent",
            border_style="cyan",
        )
    )
    return layout


def run_live(
    *,
    stop_event: threading.Event,
    worker_thread: threading.Thread,
    state: RuntimeState,
    bus: EventBus,
    refresh_stats: Callable[[], None],
) -> None:
    from rich.live import Live

    ensure_rich_available()

    def _current_layout():
        return build_layout(
            state.snapshot(),
            bus.tail(40),
            bus.cursor_lines(40),
            terminal_width=_terminal_width(),
        )

    with Live(_current_layout(), refresh_per_second=4, screen=True) as live:
        while worker_thread.is_alive() or not stop_event.is_set():
            refresh_stats()
            live.update(_current_layout())
            time.sleep(0.25)

    worker_thread.join(timeout=30.0)
