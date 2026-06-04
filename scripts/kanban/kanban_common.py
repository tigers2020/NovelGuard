#!/usr/bin/env python3
"""Local Kanban automation helpers."""

from __future__ import annotations

import argparse
import datetime as dt
import importlib.util
import json
import os
import random
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

_KANBAN_DIR = Path(__file__).resolve().parent
ROOT = _KANBAN_DIR.parents[1]
FEATURES_DIR = ROOT / ".devtool" / "features"
DONE_DIR = FEATURES_DIR / "done"
DOCS_SUPERPOWERS_PREFIX = "../../../docs/superpowers/"
DEFAULT_CONFIG_PATH = Path(".devtool/hooks/kanban_automation.json")
_SCRIPTS_DIR = ROOT / "scripts"
if str(_KANBAN_DIR) not in sys.path:
    sys.path.insert(0, str(_KANBAN_DIR))
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.append(str(_SCRIPTS_DIR))

COLUMN_ALIASES = {
    "inbox": "inbox",
    "spec-draft": "spec-draft",
    "spec-review": "spec-review",
    "plan-draft": "plan-draft",
    "plan-review": "plan-review",
    "todo": "todo",
    "scheduled": "scheduled",
    "ready-gate": "ready-gate",
    "in-progress": "in-progress",
    "verify": "verify",
    "done": "done",
    "blocked": "blocked",
    "triage": "inbox",
    "review": "verify",
    "ready": "ready-gate",
    "in_progress": "in-progress",
    "spec": "spec-draft",
    "plan": "plan-draft",
    "proposed": "todo",
    "cancelled": "blocked",
    "backlog": "inbox",
}

PIPELINE_COLUMNS = (
    "inbox",
    "spec-draft",
    "spec-review",
    "plan-draft",
    "plan-review",
    "todo",
    "scheduled",
    "in-progress",
    "verify",
    "done",
    "blocked",
)

WORKFLOW_COLUMNS = frozenset(PIPELINE_COLUMNS)


def utc_now() -> str:
    return dt.datetime.now(dt.UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def utc_date() -> str:
    return dt.datetime.now(dt.UTC).strftime("%Y-%m-%d")


def slugify(text: str, *, max_len: int | None = None) -> str:
    raw = text.strip().lower()
    raw = re.sub(r"[`'\"]+", "", raw)
    raw = re.sub(r"[^a-z0-9]+", "-", raw).strip("-")
    if max_len is not None:
        raw = raw[:max_len].strip("-")
    return raw or "work"


def repo_path(path_value: str | Path) -> Path:
    path = Path(path_value)
    if path.is_absolute():
        return path
    return ROOT / path


def rel_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def load_config(config_path: str | Path = DEFAULT_CONFIG_PATH) -> dict[str, Any]:
    path = repo_path(config_path)
    default = {
        "poll_seconds": 2,
        "inbox_empty_poll_seconds_min": 10,
        "inbox_empty_poll_seconds_max": 15,
        "board_root": ".devtool/features",
        "state_file": ".devtool/hooks/state.json",
        "events_dir": ".devtool/hooks/events",
        "logs_dir": ".devtool/hooks/logs",
        "locks_dir": ".devtool/hooks/locks",
        "prompts_dir": ".devtool/hooks/prompts",
        "oldest_scheduled_first": True,
        "auto_rework": False,
        "review_mode": "normal",
        "cursor_planning": True,
        "cursor_grill": False,
        "grill_on_blocker_only": True,
        "cursor_todo": False,
        "cursor_cli": {
            "enabled": True,
            "commands": ["agent", "cursor-agent"],
            "args": ["-p", "--trust", "--workspace", "{workspace}"],
            "prompt_prefix": "/caveman",
            "timeout_seconds": 7200,
        },
    }
    if path.exists():
        loaded = json.loads(path.read_text(encoding="utf-8"))
        default.update(loaded)
        cursor_cli = default["cursor_cli"] | loaded.get("cursor_cli", {})
        default["cursor_cli"] = cursor_cli
    for key in ("events_dir", "logs_dir", "locks_dir", "prompts_dir"):
        repo_path(default[key]).mkdir(parents=True, exist_ok=True)
    repo_path(default["board_root"]).mkdir(parents=True, exist_ok=True)
    repo_path(default["state_file"]).parent.mkdir(parents=True, exist_ok=True)
    return default


def load_state(config: dict[str, Any]) -> dict[str, Any]:
    path = repo_path(config["state_file"])
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"_blocked": "state file is invalid json"}


def save_state(config: dict[str, Any], state: dict[str, Any], *, dry_run: bool) -> None:
    if dry_run:
        return
    path = repo_path(config["state_file"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def normalize_column(value: str | None) -> str:
    raw = (value or "").strip().lower().replace("_", "-").replace(" ", "-")
    return COLUMN_ALIASES.get(raw, raw)


def normalize_status(raw: str, parent_dir: str = "") -> str:
    """Resolve card status from frontmatter and optional legacy folder name."""
    key = raw.strip()
    parent = normalize_column(parent_dir) if parent_dir else ""
    if not key and parent in WORKFLOW_COLUMNS:
        key = parent
    if not key:
        key = "inbox"
    return normalize_column(key)


def card_work_id(meta: dict[str, Any], stem: str) -> str:
    return normalize_work_id(str(meta.get("work_id") or meta.get("epic") or meta.get("id")), stem)


WORK_ID_STAGE_SUFFIXES = (
    "-spec-review",
    "-spec-draft",
    "-plan-review",
    "-plan-draft",
    "-ready-gate",
    "-in-progress",
    "-scheduled",
    "-inbox",
    "-verify",
    "-todo",
)


def strip_work_id_stage_suffix(work_id: str) -> str:
    normalized = work_id.strip().lower()
    while True:
        stripped = normalized
        for suffix in WORK_ID_STAGE_SUFFIXES:
            if normalized.endswith(suffix):
                normalized = normalized[: -len(suffix)].rstrip("-")
                break
        if normalized == stripped:
            return normalized or work_id


def normalize_work_id(value: str | None, fallback: str | None = None) -> str:
    raw = (value or fallback or "work").strip().lower()
    raw = re.sub(r"[^a-z0-9]+", "-", raw).strip("-")
    raw = strip_work_id_stage_suffix(raw or "work")
    return raw or "work"


def split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    return parse_frontmatter(parts[1]), parts[2].lstrip("\n")


def parse_scalar(value: str) -> Any:
    value = value.strip()
    if value in ("", "null", "None", "~"):
        return None
    if value in ("true", "True"):
        return True
    if value in ("false", "False"):
        return False
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [parse_scalar(part.strip()) for part in inner.split(",")]
    return value.strip("'\"")


def parse_frontmatter(block: str) -> dict[str, Any]:
    data: dict[str, Any] = {}
    current_key: str | None = None
    for raw_line in block.splitlines():
        line = raw_line.rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line.startswith("  - ") and current_key:
            if not isinstance(data.get(current_key), list):
                data[current_key] = []
            data[current_key].append(parse_scalar(line[4:]))
            continue
        if ":" in line:
            key, value = line.split(":", 1)
            current_key = key.strip()
            scalar = parse_scalar(value)
            if scalar is None and not value.strip():
                data[current_key] = []
            else:
                data[current_key] = scalar
    return data


def format_scalar(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    text = str(value)
    if any(ch in text for ch in (":", "#", "\n", "{", "}", "[", "]", ",")) or text.strip() != text:
        escaped = text.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    return text


def render_frontmatter(meta: dict[str, Any], body: str) -> str:
    lines: list[str] = ["---"]
    for key, value in meta.items():
        if isinstance(value, list):
            if not value:
                lines.append(f"{key}: []")
            else:
                lines.append(f"{key}:")
                for item in value:
                    lines.append(f"  - {format_scalar(item)}")
        else:
            lines.append(f"{key}: {format_scalar(value)}")
    lines.extend(["---", "", body.lstrip("\n")])
    return "\n".join(lines)


def read_card(path: Path) -> tuple[dict[str, Any], str]:
    return split_frontmatter(path.read_text(encoding="utf-8"))


def safe_read_card(path: Path) -> tuple[dict[str, Any], str] | None:
    """Read a card; return None when the file is missing or frontmatter is invalid."""
    try:
        return read_card(path)
    except OSError:
        return None
    except (ValueError, TypeError):
        return None


def write_card(path: Path, meta: dict[str, Any], body: str, *, dry_run: bool) -> None:
    if dry_run:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_frontmatter(meta, body), encoding="utf-8")


def update_frontmatter(path: Path, updates: dict[str, Any], *, dry_run: bool) -> None:
    meta, body = read_card(path)
    meta.update(updates)
    write_card(path, meta, body, dry_run=dry_run)


def board_root(config: dict[str, Any]) -> Path:
    return repo_path(config["board_root"])


def board_card_dir(config: dict[str, Any], column: str) -> Path:
    """Directory for a card file. Active columns live flat at features/; done uses features/done/."""
    col = normalize_column(column)
    root = board_root(config)
    if col == "done":
        done_dir = root / "done"
        done_dir.mkdir(parents=True, exist_ok=True)
        return done_dir
    return root


def column_dir(config: dict[str, Any], column: str) -> Path:
    """Legacy subfolder path — prefer board_card_dir for new writes."""
    return board_root(config) / normalize_column(column)


def scan_cards(config: dict[str, Any], column: str | None = None) -> list[Path]:
    root = board_root(config)
    cards = [path for path in root.rglob("*.md") if path.is_file()]
    if column is None:
        return sorted(cards)
    expected = normalize_column(column)
    matched: list[Path] = []
    for path in cards:
        parsed = safe_read_card(path)
        if parsed is None:
            terminal_log(f"skip unreadable card {rel_path(path)}", script="board")
            continue
        meta, _ = parsed
        parent_column = normalize_column(path.parent.name if path.parent != root else "")
        card_column = normalize_column(str(meta.get("status") or parent_column))
        if card_column == expected:
            matched.append(path)
    return sorted(matched)


def detect_drift(path: Path, config: dict[str, Any]) -> str | None:
    root = board_root(config).resolve()
    meta, _ = read_card(path)
    status = normalize_column(str(meta.get("status") or ""))
    if not status:
        return f"{rel_path(path)} missing status"
    try:
        relative = path.resolve().relative_to(root)
    except ValueError:
        return f"{rel_path(path)} outside board root"
    parent = relative.parts[0] if len(relative.parts) > 1 else ""
    parent_status = normalize_column(parent)
    if parent and parent_status in PIPELINE_COLUMNS and parent_status != status:
        return f"{rel_path(path)} folder={parent_status} frontmatter={status}"
    return None


def move_card(path: Path, column: str, config: dict[str, Any], *, dry_run: bool) -> Path:
    target_column = normalize_column(column)
    target_dir = board_card_dir(config, target_column)
    target_path = target_dir / path.name
    if dry_run and not path.exists():
        return target_path
    meta, body = read_card(path)
    source_id = str(meta.get("id") or "")
    source_work_id = normalize_work_id(
        str(meta.get("work_id") or meta.get("epic") or source_id), path.stem
    )
    meta["status"] = target_column
    if dry_run:
        return target_path
    target_dir.mkdir(parents=True, exist_ok=True)
    if path.resolve() == target_path.resolve():
        write_card(path, meta, body, dry_run=False)
        terminal_log(f"status {rel_path(path)} -> {target_column}", script="board")
        return path
    if target_path.exists():
        target_meta, target_body = read_card(target_path)
        target_id = str(target_meta.get("id") or "")
        target_work_id = normalize_work_id(
            str(target_meta.get("work_id") or target_meta.get("epic") or target_id),
            target_path.stem,
        )
        if source_id == target_id or source_work_id == target_work_id:
            target_meta["status"] = target_column
            write_card(target_path, target_meta, target_body, dry_run=False)
            if path.resolve() != target_path.resolve():
                path.unlink()
            terminal_log(
                f"merged {rel_path(path)} -> {rel_path(target_path)} status={target_column}",
                script="board",
            )
            return target_path
        raise RuntimeError(f"target already exists: {rel_path(target_path)}")
    target_path.write_text(render_frontmatter(meta, body), encoding="utf-8")
    path.unlink()
    terminal_log(
        f"move {rel_path(path)} -> {rel_path(target_path)} status={target_column}", script="board"
    )
    return target_path


def write_event(
    config: dict[str, Any],
    script_name: str,
    work_id: str,
    status: str,
    payload: dict[str, Any],
    *,
    dry_run: bool,
) -> Path:
    events_dir = repo_path(config["events_dir"])
    name = f"{utc_now().replace(':', '').replace('-', '')}-{script_name}-{work_id}-{status}.json"
    path = events_dir / name
    event = {
        "at": utc_now(),
        "script": script_name,
        "work_id": work_id,
        "status": status,
        **payload,
    }
    if not dry_run:
        events_dir.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(event, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def write_log(
    config: dict[str, Any],
    script_name: str,
    work_id: str,
    status: str,
    lines: list[str],
    *,
    dry_run: bool,
) -> Path:
    logs_dir = repo_path(config["logs_dir"])
    name = f"{utc_now().replace(':', '').replace('-', '')}-{script_name}-{work_id}-{status}.md"
    path = logs_dir / name
    content = "\n".join(
        [f"# {script_name}", "", f"- work_id: {work_id}", f"- status: {status}", *lines, ""]
    )
    if not dry_run:
        logs_dir.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return path


def append_card_section(path: Path, title: str, lines: list[str], *, dry_run: bool) -> None:
    if dry_run and not path.exists():
        return
    meta, body = read_card(path)
    stamp = utc_now()
    section = "\n".join(["", f"## {title}", "", f"_automation_at: {stamp}_", "", *lines, ""])
    write_card(path, meta, body.rstrip() + "\n" + section, dry_run=dry_run)


def read_card_links(path: Path) -> dict[str, str]:
    meta, body = read_card(path)
    links: dict[str, str] = {}
    for key in ("linked_spec", "linked_plan", "linked_todo", "branch"):
        value = meta.get(key)
        if value:
            links[key] = str(value)
    patterns = {
        "linked_spec": r"\*\*Spec\*\*\s*\|\s*`?([^`|\n]+)`?",
        "linked_plan": r"\*\*Plan\*\*\s*\|\s*`?([^`|\n]+)`?",
        "linked_todo": r"\*\*Todo card\*\*\s*\|\s*(?:\[.*?\]\()?([^)|\n]+)",
        "branch": r"\*\*Branch\*\*\s*\|\s*`?([^`|\n]+)`?",
    }
    for key, pattern in patterns.items():
        if key not in links:
            match = re.search(pattern, body)
            if match:
                links[key] = match.group(1).strip()
    return links


def expected_card_path(config: dict[str, Any], work_id: str, column: str) -> Path:
    col = normalize_column(column)
    return board_card_dir(config, col) / f"{work_id}-{col}.md"


def find_card_for_stage(config: dict[str, Any], work_id: str, column: str) -> Path | None:
    """Locate a pipeline card by work_id and stage suffix, regardless of frontmatter status."""
    path = expected_card_path(config, work_id, column)
    if path.exists():
        return path
    col = normalize_column(column)
    suffix = f"-{col}"
    matches: list[Path] = []
    for candidate in scan_cards(config):
        meta, _ = read_card(candidate)
        card_work_id = normalize_work_id(
            str(meta.get("work_id") or meta.get("epic") or meta.get("id")), candidate.stem
        )
        card_id = str(meta.get("id") or candidate.stem)
        if card_work_id == work_id and (
            card_id.endswith(suffix) or candidate.stem.endswith(suffix)
        ):
            matches.append(candidate)
    if len(matches) > 1:
        return min(matches, key=lambda p: p.name)
    return matches[0] if matches else None


def ensure_unique_card(
    config: dict[str, Any], column: str, work_id: str
) -> tuple[Path | None, str | None]:
    by_path = find_card_for_stage(config, work_id, column)
    cards = []
    for path in scan_cards(config, column):
        meta, _ = read_card(path)
        card_work_id = normalize_work_id(
            str(meta.get("work_id") or meta.get("epic") or meta.get("id")), path.stem
        )
        if card_work_id == work_id:
            cards.append(path)
    if by_path and by_path not in cards:
        cards.append(by_path)
    if len(cards) > 1:
        return (
            None,
            f"multiple {column} cards for {work_id}: {', '.join(rel_path(path) for path in cards)}",
        )
    return (cards[0], None) if cards else (None, None)


def create_card_if_missing(
    config: dict[str, Any],
    column: str,
    work_id: str,
    title: str,
    meta_updates: dict[str, Any],
    body: str,
    *,
    dry_run: bool,
) -> Path:
    existing, blocker = ensure_unique_card(config, column, work_id)
    if blocker:
        raise RuntimeError(blocker)
    if existing:
        return existing
    card_id = f"{work_id}-{normalize_column(column)}"
    path = expected_card_path(config, work_id, column)
    if path.exists():
        return path
    meta = {
        "id": card_id,
        "status": normalize_column(column),
        "work_id": work_id,
        "automation_state": "created",
    }
    meta.update(meta_updates)
    content_body = f"# {title}\n\n{body.strip()}\n"
    if not dry_run:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(render_frontmatter(meta, content_body), encoding="utf-8")
    return path


def run_command(
    command: list[str], *, cwd: Path = ROOT, timeout: int | None = None
) -> dict[str, Any]:
    started_at = utc_now()
    resolved_command = list(command)
    executable = shutil.which(resolved_command[0])
    if executable:
        resolved_command[0] = executable
    try:
        completed = subprocess.run(
            resolved_command,
            cwd=cwd,
            timeout=timeout,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            check=False,
        )
        return {
            "command": command,
            "cwd": rel_path(cwd),
            "started_at": started_at,
            "exit_code": completed.returncode,
            "stdout": (completed.stdout or "")[-4000:],
            "stderr": (completed.stderr or "")[-4000:],
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "command": command,
            "cwd": rel_path(cwd),
            "started_at": started_at,
            "exit_code": 124,
            "stdout": (exc.stdout or "")[-4000:] if isinstance(exc.stdout, str) else "",
            "stderr": f"timeout after {timeout} seconds",
        }
    except OSError as exc:
        return {
            "command": command,
            "cwd": rel_path(cwd),
            "started_at": started_at,
            "exit_code": 127,
            "stdout": "",
            "stderr": str(exc),
        }


def check_process_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def acquire_lock(
    config: dict[str, Any], name: str, content: dict[str, Any], *, dry_run: bool
) -> tuple[Path, str | None]:
    lock_path = repo_path(config["locks_dir"]) / name
    if lock_path.exists():
        try:
            current = json.loads(lock_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            current = {}
        pid = int(current.get("pid") or 0)
        if check_process_alive(pid):
            return lock_path, f"active lock: {rel_path(lock_path)} pid={pid}"
    if not dry_run:
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        lock_path.write_text(json.dumps(content, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return lock_path, None


def release_lock(path: Path, *, dry_run: bool) -> None:
    if dry_run:
        return
    if path.exists():
        path.unlink()


_SYNC_MODULE_NAME = "novelguard_kanban_sync_folders"


def _load_sync_board():
    """Load sync_board from scripts/kanban/sync_kanban_folders.py (never the root shim)."""
    cached = sys.modules.get(_SYNC_MODULE_NAME)
    if cached is not None:
        sync_board = getattr(cached, "sync_board", None)
        if sync_board is not None:
            return sync_board
    module_path = _KANBAN_DIR / "sync_kanban_folders.py"
    spec = importlib.util.spec_from_file_location(_SYNC_MODULE_NAME, module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load sync_kanban_folders from {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[_SYNC_MODULE_NAME] = module
    spec.loader.exec_module(module)
    sync_board = getattr(module, "sync_board", None)
    if sync_board is None:
        raise ImportError(f"sync_board missing in {module_path}")
    return sync_board


def run_sync_kanban_folders_if_present(*, dry_run: bool) -> list[str]:
    """Flatten subfolder cards to features/*.md (status frontmatter = column)."""
    if dry_run:
        return []
    logs = _load_sync_board()(dry_run=False)
    for line in logs:
        once_key = f"sync:skip:{line}" if line.startswith("skip ") else None
        terminal_log(f"sync: {line}", script="sync", once_key=once_key)
    if not logs:
        terminal_log("sync: board already flat", script="sync", once_key="sync:flat")
    return logs


def resolve_cursor_command(config: dict[str, Any]) -> list[str]:
    cursor_config = config.get("cursor_cli", {})
    candidates = cursor_config.get("commands")
    if not candidates:
        legacy = cursor_config.get("command")
        candidates = [legacy] if legacy else ["agent", "cursor-agent", "cursor"]
    for name in candidates:
        path = shutil.which(str(name))
        if path:
            return [path]
    return [str(candidates[0])]


def build_cursor_command(config: dict[str, Any], prompt: str) -> list[str]:
    cursor_config = config.get("cursor_cli", {})
    command = resolve_cursor_command(config)
    args = cursor_config.get("args", ["-p", "--trust", "--workspace", "{workspace}"])
    formatted: list[str] = []
    for arg in args:
        formatted.append(
            str(arg).format(
                workspace=str(ROOT),
                prompt_file="",
                repo=str(ROOT),
            )
        )
    return command + formatted + [prompt]


def wrap_cursor_prompt(prompt: str, config: dict[str, Any]) -> str:
    from cursor_cli_common import apply_prompt_prefix

    prefix = str(config.get("cursor_cli", {}).get("prompt_prefix", "/caveman"))
    return apply_prompt_prefix(prompt, prefix)


def write_prompt_file(
    config: dict[str, Any], work_id: str, phase: str, prompt: str, *, dry_run: bool
) -> Path:
    prompt_path = repo_path(config["prompts_dir"]) / f"{work_id}-{phase}.md"
    if not dry_run:
        prompt_path.parent.mkdir(parents=True, exist_ok=True)
        prompt_path.write_text(prompt, encoding="utf-8")
    return prompt_path


def run_cursor_phase(
    config: dict[str, Any],
    work_id: str,
    phase: str,
    prompt: str,
    *,
    dry_run: bool,
) -> tuple[Path, dict[str, Any] | None, str | None]:
    """Run a Kanban phase through Cursor CLI. Returns (prompt_path, result, blocker)."""
    wrapped_prompt = wrap_cursor_prompt(prompt, config)
    prompt_path = write_prompt_file(config, work_id, phase, wrapped_prompt, dry_run=dry_run)
    cursor_config = config.get("cursor_cli", {})
    if not cursor_config.get("enabled"):
        terminal_log(
            f"{work_id}: Cursor CLI blocked — not enabled (phase={phase})", script="cursor"
        )
        return prompt_path, None, "cursor_cli not configured (set cursor_cli.enabled=true)"
    if dry_run:
        terminal_log(
            f"{work_id}: Cursor CLI dry-run skip (phase={phase})",
            script="cursor",
            once_key=f"dry-run:{work_id}:{phase}",
        )
        return (
            prompt_path,
            {"command": ["dry-run"], "exit_code": 0, "stdout": "", "stderr": ""},
            None,
        )
    prompt_text = (
        prompt_path.read_text(encoding="utf-8") if prompt_path.exists() else wrapped_prompt
    )
    command = build_cursor_command(config, prompt_text)
    terminal_log(
        f"{work_id}: Cursor CLI start phase={phase} prompt={rel_path(prompt_path)}",
        script="cursor",
    )
    result = run_command(command, timeout=int(cursor_config.get("timeout_seconds", 7200)))
    terminal_log(
        f"{work_id}: Cursor CLI done phase={phase} exit_code={result['exit_code']}",
        script="cursor",
    )
    if result["exit_code"] != 0:
        return (
            prompt_path,
            result,
            f"cursor_cli {phase} failed with exit_code={result['exit_code']}",
        )
    return prompt_path, result, None


def extract_section_lines(body: str, heading: str) -> list[str]:
    pattern = re.compile(rf"^##\s+{re.escape(heading)}\s*$", re.MULTILINE)
    match = pattern.search(body)
    if not match:
        return []
    start = match.end()
    next_heading = re.search(r"^##\s+", body[start:], re.MULTILINE)
    section = body[start : start + next_heading.start()] if next_heading else body[start:]
    return [line.rstrip() for line in section.strip().splitlines() if line.strip()]


def extract_bullets(body: str, heading: str) -> list[str]:
    return [
        line[2:].strip() for line in extract_section_lines(body, heading) if line.startswith("- ")
    ]


def infer_files_allowed(body: str) -> list[str]:
    candidates: list[str] = []
    path_prefixes = ("src/", "web/", "docs/", "scripts/", ".devtool/")
    for line in body.splitlines():
        clean = line.strip().strip("`").lstrip("- ").strip()
        for prefix in path_prefixes:
            idx = clean.find(prefix)
            if idx < 0:
                continue
            fragment = clean[idx:]
            for sep in (" ", "|", ")", "`", '"', "'"):
                if sep in fragment:
                    fragment = fragment.split(sep)[0]
            candidates.append(fragment.rstrip(".,;"))
    if candidates:
        return sorted(set(candidates))
    return [".devtool/features/", "docs/agent/"]


def files_allowed_from_card(meta: dict[str, Any], body: str) -> list[str]:
    raw = meta.get("files_allowed")
    if isinstance(raw, list) and raw:
        return [str(item) for item in raw]
    if isinstance(raw, str) and raw.strip():
        return [item.strip() for item in raw.split(",") if item.strip()]
    bullets = extract_bullets(body, "files_allowed")
    if bullets:
        return bullets
    return infer_files_allowed(body)


def resolve_card_link(card_path: Path, value: str | None) -> Path | None:
    if not value:
        return None
    clean = value.strip().strip("`")
    path = Path(clean)
    if not path.is_absolute():
        path = (card_path.parent / path).resolve()
        if not path.exists():
            path = repo_path(clean)
    return path if path.exists() else None


def frontmatter_approved(path: Path | None) -> bool:
    if not path:
        return False
    meta, body = read_card(path)
    return (
        bool(meta.get("approved"))
        or str(meta.get("status")).lower() == "approved"
        or "approved" in body.lower()
    )


def normalize_doc_link(value: str) -> str:
    """Make spec/plan paths clickable from .devtool/features/."""
    prefix = DOCS_SUPERPOWERS_PREFIX
    for token in ("`specs/", "`plans/", "(../specs/", "(specs/", "(../plans/", "(plans/"):
        if token in value:
            repl = token.replace("specs/", f"{prefix}specs/").replace("plans/", f"{prefix}plans/")
            value = value.replace(token, repl)
    if value.startswith("docs/superpowers/"):
        return value.replace("docs/superpowers/", prefix, 1)
    return value


def fix_card_doc_links(text: str) -> str:
    text = text.replace("`specs/", f"`{DOCS_SUPERPOWERS_PREFIX}specs/")
    text = text.replace("`plans/", f"`{DOCS_SUPERPOWERS_PREFIX}plans/")
    text = text.replace("(../specs/", f"({DOCS_SUPERPOWERS_PREFIX}specs/")
    text = text.replace("(specs/", f"({DOCS_SUPERPOWERS_PREFIX}specs/")
    text = text.replace("(../plans/", f"({DOCS_SUPERPOWERS_PREFIX}plans/")
    text = text.replace("(plans/", f"({DOCS_SUPERPOWERS_PREFIX}plans/")
    return text


def run_verification_commands(
    changed: list[str],
    meta: dict[str, Any],
    body: str,
    *,
    include_phase_script: bool = True,
) -> list[dict[str, Any]]:
    commands: list[dict[str, Any]] = []
    verify_script = repo_path("scripts/verify_phase_completion.py")
    if include_phase_script and verify_script.exists():
        commands.append(run_command([sys.executable, str(verify_script)]))
    if any(path.startswith("web/") for path in changed):
        commands.append(run_command(["npm", "run", "lint"], cwd=repo_path("web")))
        commands.append(run_command(["npm", "run", "test:contracts"], cwd=repo_path("web")))
    listed = body.lower()
    if "e2e" in listed or meta.get("ui_e2e"):
        commands.append(run_command(["npm", "run", "test:e2e"], cwd=repo_path("web")))
    return commands


def find_changed_paths() -> list[str]:
    result = run_command(["git", "status", "--porcelain"])
    changed: list[str] = []
    for line in result.get("stdout", "").splitlines():
        if not line.strip():
            continue
        changed.append(line[3:].strip())
    return changed


def has_path_prefix(path_value: str, prefixes: list[str]) -> bool:
    clean = path_value.replace("\\", "/").lstrip("/")
    return any(
        clean == prefix.rstrip("/") or clean.startswith(prefix.rstrip("/") + "/")
        for prefix in prefixes
    )


def inbox_poll_sleep_seconds(config: dict[str, Any], result: dict[str, Any]) -> int:
    """Slower poll while Inbox has no cards; faster poll when work is present."""
    if result.get("next_action") == "no inbox cards found":
        lo = int(config.get("inbox_empty_poll_seconds_min", 10))
        hi = int(config.get("inbox_empty_poll_seconds_max", 15))
        if hi < lo:
            hi = lo
        return random.randint(lo, hi)
    return int(config.get("poll_seconds", 2))


_TERMINAL_ONCE: set[str] = set()
_TERMINAL_DEDUPE: dict[str, str] = {}


def terminal_log(
    message: str,
    *,
    script: str | None = None,
    once_key: str | None = None,
    dedupe_key: str | None = None,
) -> None:
    """Print progress to terminal. once_key=at most once per process; dedupe_key=skip until message changes."""
    if once_key and once_key in _TERMINAL_ONCE:
        return
    if dedupe_key and _TERMINAL_DEDUPE.get(dedupe_key) == message:
        return
    stamp = dt.datetime.now().strftime("%H:%M:%S")
    prefix = f"[kanban {script} {stamp}]" if script else f"[kanban {stamp}]"
    print(f"{prefix} {message}", flush=True)
    if once_key:
        _TERMINAL_ONCE.add(once_key)
    if dedupe_key:
        _TERMINAL_DEDUPE[dedupe_key] = message


def automation_result_signature(result: dict[str, Any]) -> tuple[Any, ...]:
    return (
        result.get("work_id"),
        result.get("status"),
        tuple(result.get("blockers") or []),
        result.get("next_action", ""),
    )


def emit_automation_result(
    config: dict[str, Any],
    script_name: str,
    result: dict[str, Any],
    *,
    dry_run: bool,
    last_signature: tuple[Any, ...] | None,
    verification: list[str] | None = None,
) -> tuple[tuple[Any, ...], bool]:
    signature = automation_result_signature(result)
    if last_signature is not None and signature == last_signature:
        return signature, False
    write_event(
        config,
        script_name,
        str(result.get("work_id", "none")),
        str(result.get("status", "UNKNOWN")),
        result,
        dry_run=dry_run,
    )
    write_log(
        config,
        script_name,
        str(result.get("work_id", "none")),
        str(result.get("status", "UNKNOWN")),
        [f"- {key}: {value}" for key, value in result.items()],
        dry_run=dry_run,
    )
    print_console_summary(
        script_name=script_name,
        work_id=str(result.get("work_id", "none")),
        start_column=str(result.get("start_column", "")),
        end_column=str(result.get("end_column", "")),
        status=str(result.get("status", "")),
        changed_paths=list(result.get("changed_paths") or []),
        verification=verification
        if verification is not None
        else list(result.get("verification") or []),
        blockers=list(result.get("blockers") or []),
        next_action=str(result.get("next_action", "")),
    )
    blockers = result.get("blockers") or []
    blocker_note = f" | blockers={len(blockers)}" if blockers else ""
    terminal_log(
        f"{result.get('work_id')}: {result.get('status')} "
        f"{result.get('start_column')}->{result.get('end_column')}{blocker_note} | {result.get('next_action', '')}",
        script=script_name,
    )
    return signature, True


def log_poll_sleep(script_name: str, result: dict[str, Any], sleep_seconds: int) -> None:
    next_action = str(result.get("next_action") or "")
    terminal_log(
        f"poll sleep {sleep_seconds}s (silent until state change) | {next_action}",
        script=script_name,
        once_key=f"{script_name}:poll:{next_action}",
    )


def run_automation_loop(
    script_name: str,
    config: dict[str, Any],
    state: dict[str, Any],
    *,
    dry_run: bool,
    once: bool,
    run_once_fn: Any,
    sleep_seconds_fn: Any | None = None,
    ok_statuses: tuple[str, ...] = ("OK", "IDLE"),
) -> int:
    result = run_once_fn(config, state, dry_run=dry_run)
    save_state(config, state, dry_run=dry_run)
    last_signature, _ = emit_automation_result(
        config, script_name, result, dry_run=dry_run, last_signature=None
    )
    if once:
        if dry_run:
            return 0
        return 0 if result.get("status") in ok_statuses else 1
    try:
        while True:
            sleep_seconds = (
                sleep_seconds_fn(config, result)
                if sleep_seconds_fn
                else int(config["poll_seconds"])
            )
            log_poll_sleep(script_name, result, sleep_seconds)
            time.sleep(sleep_seconds)
            result = run_once_fn(config, state, dry_run=dry_run)
            last_signature, emitted = emit_automation_result(
                config,
                script_name,
                result,
                dry_run=dry_run,
                last_signature=last_signature,
            )
            if emitted:
                save_state(config, state, dry_run=dry_run)
    except KeyboardInterrupt:
        terminal_log("stopped (Ctrl+C)", script=script_name)
        return 0


def build_parser(description: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH))
    return parser


def print_console_summary(
    *,
    script_name: str,
    work_id: str,
    start_column: str,
    end_column: str,
    status: str,
    changed_paths: list[str],
    verification: list[str],
    blockers: list[str],
    next_action: str,
) -> None:
    print("## Kanban automation")
    print(f"- Script: {script_name}")
    print(f"- Work: {work_id}")
    print(f"- Start column: {start_column}")
    print(f"- End column: {end_column}")
    print(f"- Status: {status}")
    print(f"- Changed paths: {', '.join(changed_paths) if changed_paths else 'none'}")
    print(f"- Verification: {', '.join(verification) if verification else 'none'}")
    print(f"- Blockers: {'; '.join(blockers) if blockers else 'none'}")
    print(f"- Next action: {next_action}")
