"""Rich live tail for automation log files."""

from __future__ import annotations

import re
import time
from collections import deque
from pathlib import Path

from automation.runners.config import load_config, repo_root
from automation.runners.log_tail import read_log_tail
from automation.runners.tui_dashboard import ensure_rich_available

_LOG_META_PREFIXES = ("prompt_log:", "delivery:", "command:", "stdin_file:")
_ISSUE_RE = re.compile(r"\bNOV-\d+\b")


def logs_dir(cfg: dict | None = None) -> Path:
    cfg = cfg or load_config()
    raw = Path((cfg.get("logs") or {}).get("dir") or "automation/logs")
    if not raw.is_absolute():
        raw = repo_root() / raw
    return raw


def newest_log(pattern: str, *, cfg: dict | None = None) -> Path | None:
    directory = logs_dir(cfg)
    if not directory.is_dir():
        return None
    matches = list(directory.glob(pattern))
    if not matches:
        return None
    return max(matches, key=lambda p: p.stat().st_mtime)


def filter_log_lines(lines: list[str]) -> list[str]:
    filtered = [ln for ln in lines if ln.strip() and not ln.startswith(_LOG_META_PREFIXES)]
    return filtered if filtered else lines


def style_log_line(line: str):
    """Return a Rich Text line with lightweight syntax highlighting."""
    from rich.text import Text

    text = Text()
    lower = line.lower()

    if line.startswith("--- ") and line.endswith(" ---"):
        text.append(line, style="bold magenta")
        return text

    if "traceback" in lower or "error" in lower or " failed" in lower:
        text.append(line, style="bold red")
        return text

    if line.startswith("[daemon]") or line.startswith("[webhook]"):
        text.append(line, style="cyan")
        return text

    if line.startswith("[worker]"):
        text.append(line, style="yellow")
        return text

    if "verify" in lower and ("ok=" in lower or "exit" in lower):
        text.append(line, style="green")
        return text

    issue_match = _ISSUE_RE.search(line)
    if issue_match:
        start, end = issue_match.span()
        text.append(line[:start])
        text.append(line[start:end], style="bold green")
        text.append(line[end:])
        return text

    if line.startswith("stderr:") or line.startswith("stdout:"):
        text.append(line, style="dim")
        return text

    text.append(line)
    return text


def build_log_panel(
    *,
    path: Path | None,
    lines: list[str],
    log_age_s: float | None,
    max_display: int = 40,
) -> object:
    from rich.panel import Panel
    from rich.text import Text

    body = Text()
    display = filter_log_lines(lines)[-max_display:]
    if not display:
        body.append("(no log output yet)", style="dim")
    else:
        for idx, line in enumerate(display):
            if idx:
                body.append("\n")
            body.append_text(style_log_line(line))

    title = path.name if path else "automation log"
    subtitle = ""
    if path:
        subtitle = str(path)
        if log_age_s is not None:
            subtitle += f"  ·  updated {int(log_age_s)}s ago"

    return Panel(body, title=title, subtitle=subtitle, border_style="blue")


class LogFollower:
    """Incrementally follow a log file."""

    def __init__(self, path: Path, *, max_lines: int = 300) -> None:
        self.path = path
        self.max_lines = max_lines
        self._lines: deque[str] = deque(maxlen=max_lines)
        self._offset = 0
        self._partial = ""
        self._load_initial()

    def _load_initial(self) -> None:
        tail, _ = read_log_tail(str(self.path), max_lines=self.max_lines)
        self._lines.extend(tail)
        try:
            self._offset = self.path.stat().st_size
        except OSError:
            self._offset = 0

    def _read_new_lines(self) -> list[str]:
        try:
            with self.path.open("rb") as handle:
                handle.seek(self._offset)
                chunk = handle.read()
                self._offset = handle.tell()
        except OSError:
            return []
        if not chunk:
            return []
        text = self._partial + chunk.decode("utf-8", errors="replace")
        parts = text.splitlines()
        if text and not text.endswith(("\n", "\r")):
            self._partial = parts.pop() if parts else text
        else:
            self._partial = ""
        return [ln.rstrip("\r") for ln in parts]

    def poll(self) -> tuple[list[str], float | None]:
        if not self.path.is_file():
            return list(self._lines), None
        for line in self._read_new_lines():
            if line:
                self._lines.append(line)
        try:
            age = max(0.0, time.time() - self.path.stat().st_mtime)
        except OSError:
            age = None
        return list(self._lines), age


def run_live_watch(
    path: Path,
    *,
    refresh_hz: float = 4.0,
    max_display: int = 40,
    pick_latest: bool = False,
    glob_pattern: str = "job-*.log",
) -> int:
    ensure_rich_available()
    from rich.live import Live

    follower: LogFollower | None = None
    current: Path | None = None
    sleep_s = 1.0 / max(refresh_hz, 0.5)

    def _resolve() -> Path | None:
        if pick_latest:
            return newest_log(glob_pattern)
        return path if path.is_file() else None

    with Live(console=None, refresh_per_second=refresh_hz, screen=True) as live:
        try:
            while True:
                target = _resolve()
                if target is None:
                    from rich.panel import Panel
                    from rich.text import Text

                    live.update(
                        Panel(
                            Text(f"No log file in {logs_dir()}", style="dim"),
                            title="automation log watch",
                            border_style="red",
                        )
                    )
                    time.sleep(sleep_s)
                    continue

                if follower is None or target != current:
                    current = target
                    follower = LogFollower(target)

                assert follower is not None
                lines, age = follower.poll()
                live.update(
                    build_log_panel(
                        path=current,
                        lines=lines,
                        log_age_s=age,
                        max_display=max_display,
                    )
                )
                time.sleep(sleep_s)
        except KeyboardInterrupt:
            return 0
