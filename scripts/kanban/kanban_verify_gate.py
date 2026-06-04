#!/usr/bin/env python3
"""Verify cards and move them to Done or back to In Progress."""

from __future__ import annotations

import sys
from pathlib import Path

from kanban_common import (
    append_card_section,
    build_parser,
    detect_drift,
    files_allowed_from_card,
    find_changed_paths,
    has_path_prefix,
    load_config,
    load_state,
    move_card,
    normalize_work_id,
    read_card,
    rel_path,
    repo_path,
    run_automation_loop,
    run_cursor_phase,
    run_sync_kanban_folders_if_present,
    run_verification_commands,
    scan_cards,
    terminal_log,
    update_frontmatter,
)

SCRIPT_NAME = "kanban_verify_gate"


def build_code_review_prompt(card_path: Path, work_id: str) -> str:
    return f"""You are working on NovelGuard.

/requesting-code-review

Goal:
Complete the Verify column review for this work item.

Rules:
- Follow AGENTS.md and docs/agent/KANBAN-detail.md.
- Do not add new scope. Fix only blocking verification gaps.
- Edit only this verify card: {rel_path(card_path)}
- Record implementation summary, exit codes, and gap matrix on the card.

Inputs:
- work_id: {work_id}

Fill on the verify card:
- Implementation summary with changed paths and commands run
- Gap matrix (spec vs plan vs implementation)
- Recorded exit codes for verification commands
- Final recommendation: pass to Done or return to In Progress with feedback
"""


def allowed_paths(meta: dict, body: str) -> list[str]:
    return files_allowed_from_card(meta, body)


def run_quality_checks(card_path: Path, changed: list[str]) -> list[dict]:
    meta, body = read_card(card_path)
    return run_verification_commands(changed, meta, body)


def append_drift_blocker(blockers: list[str], card_path: Path, config: dict) -> None:
    drift = detect_drift(card_path, config)
    if drift:
        blockers.append(drift)


def append_files_allowed_blockers(blockers: list[str], meta: dict, body: str, changed: list[str]) -> None:
    allowed = allowed_paths(meta, body)
    if not allowed:
        blockers.append("files_allowed missing")
        return
    product_changed = [path for path in changed if path.startswith(("src/", "web/"))]
    outside = [path for path in product_changed if not has_path_prefix(path, allowed)]
    if outside:
        blockers.append(f"changed paths outside files_allowed: {', '.join(outside)}")


def append_documentation_blockers(blockers: list[str], meta: dict, body: str) -> None:
    lowered = body.lower()
    if "implementation summary" not in lowered:
        blockers.append("implementation summary missing")
    if "exit_code" not in lowered:
        blockers.append("recorded exit codes missing")
    if "acceptance" not in lowered and not meta.get("acceptance"):
        blockers.append("acceptance evidence missing")


def append_destructive_operation_blockers(blockers: list[str], meta: dict, body: str) -> None:
    lowered = body.lower()
    if "remove-item" not in lowered and " rm " not in lowered:
        return
    if "dry-run" not in lowered or not meta.get("approved"):
        blockers.append("destructive operation evidence lacks dry-run and approval")


def append_new_test_blockers(blockers: list[str], meta: dict, changed: list[str]) -> None:
    new_tests = [
        path
        for path in changed
        if path.endswith((".test.ts", "_test.py", "test.py"))
        and path.startswith(("tests/", "web/src/"))
    ]
    if new_tests and not meta.get("approved_new_tests"):
        blockers.append(f"new test files without explicit approval: {', '.join(new_tests)}")


def append_quality_command_blockers(blockers: list[str], quality: list[dict]) -> None:
    for item in quality:
        if item["exit_code"] != 0:
            blockers.append(f"quality command failed: {item['command']} exit_code={item['exit_code']}")


def review_card(card_path: Path, config: dict, *, dry_run: bool) -> tuple[list[str], list[str], list[dict]]:
    meta, body = read_card(card_path)
    blockers: list[str] = []
    changed = find_changed_paths()
    append_drift_blocker(blockers, card_path, config)
    append_files_allowed_blockers(blockers, meta, body, changed)
    append_documentation_blockers(blockers, meta, body)
    append_destructive_operation_blockers(blockers, meta, body)
    append_new_test_blockers(blockers, meta, changed)
    quality = [] if dry_run else run_quality_checks(card_path, changed)
    append_quality_command_blockers(blockers, quality)
    return blockers, changed, quality


def update_optional_closeout_files(*, dry_run: bool) -> list[str]:
    changed: list[str] = []
    changelog = repo_path("CHANGELOG-agent.md")
    if changelog.exists():
        if not dry_run:
            changelog.write_text(changelog.read_text(encoding="utf-8").rstrip() + "\n\n- Kanban verify gate closed a card.\n", encoding="utf-8")
        changed.append(rel_path(changelog))
    agent_state = repo_path("AGENT_STATE.json")
    if agent_state.exists():
        changed.append(rel_path(agent_state))
    return changed


def run_once(config: dict, state: dict, *, dry_run: bool) -> dict:
    run_sync_kanban_folders_if_present(dry_run=dry_run)
    verify_cards = scan_cards(config, "verify")
    terminal_log(
        f"verify scan: {len(verify_cards)} card(s)",
        script=SCRIPT_NAME,
        dedupe_key=f"{SCRIPT_NAME}:verify_count",
    )
    if not verify_cards:
        return {
            "work_id": "none",
            "start_column": "verify",
            "end_column": "verify",
            "status": "IDLE",
            "changed_paths": [],
            "verification": [],
            "blockers": [],
            "next_action": "no verify cards found",
        }
    card_path = verify_cards[0]
    meta, _ = read_card(card_path)
    work_id = normalize_work_id(str(meta.get("work_id") or meta.get("epic") or meta.get("id")), card_path.stem)
    terminal_log(f"{work_id}: verify gate on {rel_path(card_path)}", script=SCRIPT_NAME)

    review_prompt = build_code_review_prompt(card_path, work_id)
    terminal_log(f"{work_id}: code-review phase (Cursor CLI)", script=SCRIPT_NAME)
    prompt_path, cursor_result, cursor_blocker = run_cursor_phase(
        config,
        work_id,
        "code-review",
        review_prompt,
        dry_run=dry_run,
    )
    if cursor_blocker:
        append_card_section(
            card_path,
            "Automation Feedback",
            [f"- Prompt: {rel_path(prompt_path)}", f"- BLOCKED: {cursor_blocker}"],
            dry_run=dry_run,
        )
        return {
            "work_id": work_id,
            "start_column": "verify",
            "end_column": "verify",
            "status": "BLOCKED",
            "changed_paths": [rel_path(card_path), rel_path(prompt_path)],
            "verification": [],
            "blockers": [cursor_blocker],
            "next_action": "run /requesting-code-review with Cursor CLI",
        }
    if cursor_result:
        state[f"{work_id}:code-review-cursor-exit-code"] = cursor_result["exit_code"]

    blockers, changed, quality = review_card(card_path, config, dry_run=dry_run)
    verification = [f"{item['command']} => {item['exit_code']}" for item in quality]
    if blockers:
        feedback = []
        for index, blocker in enumerate(blockers, start=1):
            feedback.extend(
                [
                    f"- issue id: VG-{index}",
                    "- severity: blocking",
                    f"- affected file: {rel_path(card_path)}",
                    f"- evidence: {blocker}",
                    "- required fix: address evidence and rerun verification",
                    "- verification to rerun: listed quality commands",
                ]
            )
        append_card_section(card_path, "Review Feedback", feedback, dry_run=dry_run)
        update_frontmatter(card_path, {"automation_state": "needs_rework", "blocked_reason": "; ".join(blockers)}, dry_run=dry_run)
        target = move_card(card_path, "in-progress", config, dry_run=dry_run)
        terminal_log(f"{work_id}: verify FAILED -> in-progress rework", script=SCRIPT_NAME)
        run_sync_kanban_folders_if_present(dry_run=dry_run)
        return {
            "work_id": work_id,
            "start_column": "verify",
            "end_column": "in-progress",
            "status": "FAILED",
            "changed_paths": [rel_path(target), *changed],
            "verification": verification,
            "blockers": blockers,
            "next_action": "rework feedback; script 2 may pick up only if configured",
        }

    closeout_lines = [
        "- status: done",
        "## Changed paths",
        *[f"- {path}" for path in changed],
        "## Verification commands",
        *[f"- {line}" for line in verification],
        "## Risks",
        "- No known blocking risks from automated verify gate.",
        "## Known limitations",
        "- Automated review is conservative and does not replace human product review.",
    ]
    append_card_section(card_path, "Final Closeout", closeout_lines, dry_run=dry_run)
    optional_changes = update_optional_closeout_files(dry_run=dry_run)
    done_path = move_card(card_path, "done", config, dry_run=dry_run)
    terminal_log(f"{work_id}: verify OK -> done", script=SCRIPT_NAME)
    run_sync_kanban_folders_if_present(dry_run=dry_run)
    state[f"{work_id}:verify-closed"] = True
    return {
        "work_id": work_id,
        "start_column": "verify",
        "end_column": "done",
        "status": "OK",
        "changed_paths": [rel_path(done_path), *changed, *optional_changes],
        "verification": verification,
        "blockers": [],
        "next_action": "manual closeout review",
    }


def main() -> int:
    parser = build_parser("Verify gate Kanban automation")
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
    )


if __name__ == "__main__":
    sys.exit(main())
