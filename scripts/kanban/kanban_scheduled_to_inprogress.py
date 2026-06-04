#!/usr/bin/env python3
"""Move one Scheduled card to In Progress and optionally run Cursor CLI."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from kanban_common import (
    acquire_lock,
    append_card_section,
    build_parser,
    detect_drift,
    find_changed_paths,
    frontmatter_approved,
    load_config,
    load_state,
    move_card,
    normalize_work_id,
    read_card,
    read_card_links,
    rel_path,
    release_lock,
    resolve_card_link,
    run_automation_loop,
    run_cursor_phase,
    run_sync_kanban_folders_if_present,
    run_verification_commands,
    scan_cards,
    terminal_log,
)

SCRIPT_NAME = "kanban_scheduled_to_inprogress"


def scheduled_sort_key(path: Path) -> tuple[str, str, str]:
    meta, _ = read_card(path)
    return (str(meta.get("order") or ""), str(meta.get("created") or ""), path.name)


def dedupe_scheduled_by_work_id(cards: list[Path]) -> list[Path]:
    ordered = sorted(cards, key=scheduled_sort_key)
    seen: set[str] = set()
    unique: list[Path] = []
    for path in ordered:
        meta, _ = read_card(path)
        work_id = normalize_work_id(str(meta.get("work_id") or meta.get("epic") or meta.get("id")), path.stem)
        if work_id in seen:
            terminal_log(f"skip duplicate scheduled card {rel_path(path)} (work_id={work_id})", script=SCRIPT_NAME)
            continue
        seen.add(work_id)
        unique.append(path)
    return unique


def _resolve_scheduled_links(
    card_path: Path, meta: dict, links: dict
) -> tuple[Path | None, Path | None, Path | None]:
    def link(key: str) -> Path | None:
        return resolve_card_link(card_path, str(meta.get(key) or links.get(key) or ""))

    return link("linked_spec"), link("linked_plan"), link("linked_todo")


def _linked_artifact_blockers(
    spec_path: Path | None,
    plan_path: Path | None,
    todo_path: Path | None,
) -> list[str]:
    blockers: list[str] = []
    for path, missing_msg, approval_msg in (
        (spec_path, "linked spec missing", "spec not approved"),
        (plan_path, "linked plan missing", "plan not approved"),
        (todo_path, "linked todo missing", None),
    ):
        if not path:
            blockers.append(missing_msg)
        elif approval_msg and not frontmatter_approved(path):
            blockers.append(approval_msg)
    return blockers


def _card_scope_blockers(meta: dict, body: str) -> list[str]:
    blockers: list[str] = []
    if not meta.get("files_allowed") and "files_allowed" not in body:
        blockers.append("files_allowed missing")
    if not meta.get("acceptance") and "acceptance" not in body.lower():
        blockers.append("acceptance missing")
    return blockers


def _default_branch(card_path: Path, meta: dict, links: dict) -> str:
    branch = str(meta.get("branch") or links.get("branch") or "")
    if branch:
        return branch
    return f"feat/{normalize_work_id(str(meta.get('work_id') or meta.get('id')), card_path.stem)}"


def gate_check(card_path: Path, config: dict) -> tuple[list[str], dict]:
    meta, body = read_card(card_path)
    links = read_card_links(card_path)
    blockers: list[str] = []
    drift = detect_drift(card_path, config)
    if drift:
        blockers.append(drift)
    spec_path, plan_path, todo_path = _resolve_scheduled_links(card_path, meta, links)
    blockers.extend(_linked_artifact_blockers(spec_path, plan_path, todo_path))
    blockers.extend(_card_scope_blockers(meta, body))
    branch = _default_branch(card_path, meta, links)
    if meta.get("blocked_reason"):
        blockers.append(f"unresolved blocker: {meta['blocked_reason']}")
    return blockers, {"spec_path": spec_path, "plan_path": plan_path, "todo_path": todo_path, "branch": branch}


def build_prompt(card_path: Path, details: dict, meta: dict, body: str) -> str:
    files_allowed = meta.get("files_allowed") or "See active card."
    acceptance = meta.get("acceptance") or "See active card."
    return f"""You are working on NovelGuard.

Follow AGENTS.md and repository Kanban gates.

Active card: {rel_path(card_path)}
Linked spec: {rel_path(details["spec_path"]) if details.get("spec_path") else "missing"}
Linked plan: {rel_path(details["plan_path"]) if details.get("plan_path") else "missing"}
Linked todo: {rel_path(details["todo_path"]) if details.get("todo_path") else "missing"}

files_allowed:
{files_allowed}

acceptance:
{acceptance}

Instructions:
- Edit only allowed paths.
- Do not create new test files unless explicitly approved.
- Stop on failing verification.
- Produce changed paths and commands run.

Card body:
{body}
"""


def run_verification(card_path: Path) -> list[dict]:
    meta, body = read_card(card_path)
    return run_verification_commands(find_changed_paths(), meta, body)


def run_once(config: dict, state: dict, *, dry_run: bool) -> dict:
    run_sync_kanban_folders_if_present(dry_run=dry_run)
    scheduled = dedupe_scheduled_by_work_id(scan_cards(config, "scheduled"))
    terminal_log(
        f"scheduled scan: {len(scheduled)} unique card(s)",
        script=SCRIPT_NAME,
        dedupe_key=f"{SCRIPT_NAME}:scheduled_count",
    )
    if not scheduled:
        return {
            "work_id": "none",
            "start_column": "scheduled",
            "end_column": "scheduled",
            "status": "IDLE",
            "changed_paths": [],
            "verification": [],
            "blockers": [],
            "next_action": "no scheduled cards found",
        }
    if len(scheduled) > 1 and not config.get("oldest_scheduled_first"):
        return {
            "work_id": "multiple",
            "start_column": "scheduled",
            "end_column": "scheduled",
            "status": "BLOCKED",
            "changed_paths": [rel_path(path) for path in scheduled],
            "verification": [],
            "blockers": ["multiple scheduled cards and oldest_scheduled_first is false"],
            "next_action": "select one scheduled card or enable oldest_scheduled_first",
        }
    if len(scheduled) > 1:
        terminal_log(
            f"picking oldest scheduled: {rel_path(scheduled[0])} ({len(scheduled) - 1} more queued)",
            script=SCRIPT_NAME,
            once_key=f"{SCRIPT_NAME}:oldest_pick",
        )
    card_path = scheduled[0]
    meta, body = read_card(card_path)
    work_id = normalize_work_id(str(meta.get("work_id") or meta.get("epic") or meta.get("id")), card_path.stem)
    terminal_log(f"{work_id}: ready-gate check on {rel_path(card_path)}", script=SCRIPT_NAME)
    blockers, details = gate_check(card_path, config)
    if blockers:
        terminal_log(f"{work_id}: ready-gate BLOCKED: {'; '.join(blockers)}", script=SCRIPT_NAME)
        append_card_section(card_path, "Automation Gate Feedback", [f"- BLOCKED: {item}" for item in blockers], dry_run=dry_run)
        return {
            "work_id": work_id,
            "start_column": "scheduled",
            "end_column": "scheduled",
            "status": "BLOCKED",
            "changed_paths": [rel_path(card_path)],
            "verification": [],
            "blockers": blockers,
            "next_action": "fix scheduled gate metadata",
        }

    in_progress_path = move_card(card_path, "in-progress", config, dry_run=dry_run)
    terminal_log(f"{work_id}: moved scheduled -> in-progress", script=SCRIPT_NAME)
    run_sync_kanban_folders_if_present(dry_run=dry_run)
    lock_path, lock_blocker = acquire_lock(
        config,
        "cursor-cli.lock",
        {"work_id": work_id, "card_path": rel_path(in_progress_path), "started_at": "now", "pid": os.getpid()},
        dry_run=dry_run,
    )
    if lock_blocker:
        return {
            "work_id": work_id,
            "start_column": "scheduled",
            "end_column": "in-progress",
            "status": "BUSY",
            "changed_paths": [rel_path(in_progress_path)],
            "verification": [],
            "blockers": [lock_blocker],
            "next_action": "wait for active cursor cli lock",
        }

    prompt_text = build_prompt(in_progress_path, details, meta, body)
    terminal_log(f"{work_id}: implementation phase (Cursor CLI)", script=SCRIPT_NAME)
    prompt_path, cursor_result, cursor_blocker = run_cursor_phase(
        config,
        work_id,
        "implementation",
        prompt_text,
        dry_run=dry_run,
    )
    if cursor_blocker:
        append_card_section(
            in_progress_path,
            "Implementation Blocked",
            [f"- Cursor prompt: {rel_path(prompt_path)}", f"- BLOCKED: {cursor_blocker}"],
            dry_run=dry_run,
        )
        release_lock(lock_path, dry_run=dry_run)
        return {
            "work_id": work_id,
            "start_column": "scheduled",
            "end_column": "in-progress",
            "status": "BLOCKED",
            "changed_paths": [rel_path(in_progress_path), rel_path(prompt_path)],
            "verification": [],
            "blockers": [cursor_blocker],
            "next_action": "fix Cursor CLI or run implementation prompt manually",
        }

    implementation = cursor_result or {"command": ["unknown"], "exit_code": 1, "stdout": "", "stderr": ""}
    verification_results = [] if dry_run else run_verification(in_progress_path)
    failed = implementation["exit_code"] != 0 or any(item["exit_code"] != 0 for item in verification_results)
    changed_paths = find_changed_paths() if not dry_run else []
    lines = [
        "### Cursor CLI",
        f"- command: `{implementation.get('command', ['unknown'])}`",
        f"- exit_code: {implementation['exit_code']}",
        "### Verification",
        *[f"- `{item['command']}` exit_code={item['exit_code']}" for item in verification_results],
        "### Changed paths",
        *[f"- {path}" for path in changed_paths],
    ]
    append_card_section(in_progress_path, "Implementation Summary", lines, dry_run=dry_run)
    if failed:
        release_lock(lock_path, dry_run=dry_run)
        return {
            "work_id": work_id,
            "start_column": "scheduled",
            "end_column": "in-progress",
            "status": "FAILED",
            "changed_paths": [rel_path(in_progress_path), *changed_paths],
            "verification": [f"{item['command']} => {item['exit_code']}" for item in verification_results],
            "blockers": ["implementation or verification failed"],
            "next_action": "fix failure feedback in in-progress",
        }

    verify_path = move_card(in_progress_path, "verify", config, dry_run=dry_run)
    terminal_log(f"{work_id}: moved in-progress -> verify", script=SCRIPT_NAME)
    run_sync_kanban_folders_if_present(dry_run=dry_run)
    release_lock(lock_path, dry_run=dry_run)
    state[f"{work_id}:implementation-completed"] = True
    return {
        "work_id": work_id,
        "start_column": "scheduled",
        "end_column": "verify",
        "status": "OK",
        "changed_paths": [rel_path(verify_path), *changed_paths],
        "verification": [f"{item['command']} => {item['exit_code']}" for item in verification_results],
        "blockers": [],
        "next_action": "run verify gate",
    }


def main() -> int:
    parser = build_parser("Scheduled to In Progress Kanban automation")
    args = parser.parse_args()
    config = load_config(args.config)
    state = load_state(config)
    return run_automation_loop(
        SCRIPT_NAME,
        config,
        state,
        dry_run=args.dry_run,
        once=args.once,
        run_once_fn=run_once,
        ok_statuses=("OK", "IDLE", "BUSY"),
    )


if __name__ == "__main__":
    sys.exit(main())
