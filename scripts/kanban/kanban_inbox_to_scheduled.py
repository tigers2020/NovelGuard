#!/usr/bin/env python3
"""Advance Inbox cards through local Kanban planning gates."""

from __future__ import annotations

import re
import sys
from pathlib import Path

from kanban_common import (
    append_card_section,
    build_parser,
    create_card_if_missing,
    detect_drift,
    ensure_unique_card,
    extract_bullets,
    files_allowed_from_card,
    find_card_for_stage,
    inbox_poll_sleep_seconds,
    load_config,
    load_state,
    move_card,
    normalize_column,
    normalize_work_id,
    read_card,
    rel_path,
    run_automation_loop,
    run_cursor_phase,
    run_sync_kanban_folders_if_present,
    scan_cards,
    terminal_log,
    update_frontmatter,
    write_card,
    write_prompt_file,
)

SCRIPT_NAME = "kanban_inbox_to_scheduled"

PLAN_PLACEHOLDER_MARKERS = (
    "Implement the approved acceptance criteria inside files_allowed only.",
    "Record changed paths and verification commands.",
)

HEADING_ACCEPTANCE_CRITERIA = "## Acceptance criteria"
HEADING_IMPLEMENTATION_TASKS = "## Implementation tasks"
SECTION_IMPLEMENTATION_TASKS = "Implementation tasks"
INBOX_ACCEPTANCE_FALLBACK = "See source Inbox card."
SECTION_AUTOMATION_FEEDBACK = "Automation Feedback"


def _step(work_id: str, message: str) -> None:
    terminal_log(f"{work_id}: {message}", script=SCRIPT_NAME)


def _pipeline_result(
    work_id: str,
    *,
    status: str,
    start_column: str,
    end_column: str,
    changed_paths: list[str],
    blockers: list[str] | None = None,
    next_action: str,
) -> dict:
    return {
        "work_id": work_id,
        "status": status,
        "start_column": start_column,
        "end_column": end_column,
        "changed_paths": changed_paths,
        "blockers": blockers or [],
        "next_action": next_action,
    }


def _blocked(
    work_id: str,
    *,
    start_column: str,
    end_column: str,
    changed_paths: list[str],
    blockers: list[str],
    next_action: str,
) -> dict:
    return _pipeline_result(
        work_id,
        status="BLOCKED",
        start_column=start_column,
        end_column=end_column,
        changed_paths=changed_paths,
        blockers=blockers,
        next_action=next_action,
    )


def _inbox_acceptance_from(meta: dict) -> str:
    return str(meta.get("acceptance") or INBOX_ACCEPTANCE_FALLBACK)


def append_blocked_feedback(card_path: Path, blockers: list[str], *, dry_run: bool) -> None:
    append_card_section(
        card_path,
        SECTION_AUTOMATION_FEEDBACK,
        [f"- BLOCKED: {item}" for item in blockers],
        dry_run=dry_run,
    )


def append_cursor_blocked_feedback(
    card_path: Path, prompt_path: Path, cursor_blocker: str, *, dry_run: bool
) -> None:
    append_card_section(
        card_path,
        SECTION_AUTOMATION_FEEDBACK,
        [f"- Prompt: {rel_path(prompt_path)}", f"- BLOCKED: {cursor_blocker}"],
        dry_run=dry_run,
    )


def has_acceptance(meta: dict, body: str) -> bool:
    if meta.get("acceptance"):
        return True
    lower = body.lower()
    if "acceptance" in lower:
        return True
    if "## exit" in lower:
        return True
    if "**spec**" in lower and "specs/" in lower:
        return True
    if "## ask" in lower and ("## scope" in lower or "files_allowed" in lower):
        return True
    return False


def inbox_sort_key(path: Path) -> tuple[str, str]:
    meta, _ = read_card(path)
    return (str(meta.get("order") or ""), path.name)


def inbox_skip_reason(card_path: Path, config: dict) -> str | None:
    meta, _ = read_card(card_path)
    work_id = normalize_work_id(str(meta.get("work_id") or meta.get("epic") or meta.get("id")), card_path.stem)
    if str(meta.get("automation_state") or "").lower() == "consumed":
        return "inbox consumed"
    scheduled_path, _ = ensure_unique_card(config, "scheduled", work_id)
    if scheduled_path:
        return "already scheduled"
    return None


def files_allowed(meta: dict, body: str) -> list[str]:
    return files_allowed_from_card(meta, body)


def build_brainstorming_prompt(card_path: Path, spec_path: Path, work_id: str, allowed: list[str], acceptance: str, inbox_body: str) -> str:
    return f"""You are working on NovelGuard.

/brainstorming

Goal:
Turn the Inbox card into a Spec Draft card.

Rules:
- Follow AGENTS.md and docs/agent/KANBAN-detail.md.
- This is planning only. Do not edit product code.
- Edit only this target card: {rel_path(spec_path)}
- Do not delete or move audit cards.
- Do not create test files.
- Use snake_case for variables if code examples are unavoidable.
- Korean comments only if code comments are unavoidable.

Inputs:
- Inbox card: {rel_path(card_path)}
- work_id: {work_id}
- files_allowed proposal: {", ".join(allowed)}
- acceptance: {acceptance}

Write the target Spec Draft card with:
- Problem
- Goals
- Non-goals
- Decisions
- UX impact
- Backend impact
- Safety impact
- Acceptance criteria
- files_allowed proposal

Inbox body:
{inbox_body}
"""


def build_writing_plans_prompt(spec_path: Path, plan_path: Path, work_id: str, allowed: list[str], branch: str) -> str:
    _, spec_body = read_card(spec_path)
    spec_excerpt = spec_body.strip()[:4000]
    return f"""You are working on NovelGuard.

/writing-plans

Goal:
Turn the approved Spec card into a detailed Plan Draft card that an engineer with zero codebase context can execute.

Rules:
- Follow AGENTS.md and docs/agent/KANBAN-detail.md.
- This is planning only. Do not edit product code.
- Edit only this target card: {rel_path(plan_path)}
- Read this spec card: {rel_path(spec_path)}
- Do not delete Spec/Plan/Todo audit cards.
- Do not create test files.
- Replace ALL automation placeholder bullets — do not leave generic one-liners.
- Use snake_case for variables if code examples are unavoidable.
- Korean comments only if code comments are unavoidable.

Inputs:
- work_id: {work_id}
- files_allowed: {", ".join(allowed)}
- branch: {branch}

Spec excerpt (read the full spec card on disk):
{spec_excerpt}

Write the target Plan Draft card with:
- Spec link
- Architecture (2-3 sentences: approach and main modules touched)
- Implementation tasks — at least 4 spec-specific tasks; each task names concrete files/modules from the spec scope
- Files allowed
- Verification matrix — one row per acceptance criterion with an exact command (pytest path, npm script, etc.)
- Risks
- Rollback plan
- Branch name
"""


def build_todo_prompt(plan_path: Path, spec_path: Path, todo_path: Path, work_id: str, allowed: list[str]) -> str:
    _, plan_body = read_card(plan_path)
    plan_excerpt = plan_body.strip()[:4000]
    return f"""You are working on NovelGuard.

Goal:
Turn the approved Plan into a Todo checklist card with bite-sized implementation chunks.

Rules:
- Follow AGENTS.md and docs/agent/KANBAN-detail.md.
- Planning only. Do not edit product code.
- Edit only this target card: {rel_path(todo_path)}
- Read plan: {rel_path(plan_path)}
- Read spec: {rel_path(spec_path)}
- Do not delete audit cards.
- Replace placeholder T1 — derive checklist items from Implementation tasks in the plan.

Inputs:
- work_id: {work_id}
- files_allowed: {", ".join(allowed)}

Plan excerpt (read the full plan card on disk):
{plan_excerpt}

Write ## Checklist with one item per plan task (T1, T2, …). Each item must include:
- files_allowed: subset paths for that chunk
- expected verification: exact command to run after the chunk
- risk: one concrete risk for that chunk
"""


def is_generic_plan_body(body: str) -> bool:
    return all(marker in body for marker in PLAN_PLACEHOLDER_MARKERS)


def is_generic_todo_body(body: str) -> bool:
    checklist = [line for line in body.splitlines() if line.strip().startswith("- [ ]")]
    if len(checklist) <= 1 and any("T1" in line for line in checklist):
        return True
    return len(checklist) == 0


def reset_plan_for_rework(plan_path: Path, config: dict, *, dry_run: bool) -> Path:
    meta, body = read_card(plan_path)
    meta.update(
        {
            "approved": None,
            "approved_by": None,
            "approved_at": None,
            "automation_state": "created",
        }
    )
    if normalize_column(str(meta.get("status") or "")) == "plan-review":
        return move_card(plan_path, "plan-draft", config, dry_run=dry_run)
    write_card(plan_path, meta, body, dry_run=dry_run)
    return plan_path


def build_grill_spec_prompt(spec_path: Path, inbox_path: Path, work_id: str) -> str:
    return f"""You are working on NovelGuard.

/grill-me

Goal:
Review the Spec card for blocking gaps before approval.

Rules:
- Follow AGENTS.md and docs/agent/KANBAN-detail.md.
- Planning only. Do not edit product code under src/ or web/.
- Edit only this target card: {rel_path(spec_path)}
- Read source Inbox: {rel_path(inbox_path)}
- Record approval on the spec card only when no blocking gaps remain.

Inputs:
- work_id: {work_id}

Write or update on the spec card:
- Internal Grill Review section with pass/fail and any blockers
- Set frontmatter approved=true only when ready for Plan Draft
"""


def build_grill_plan_prompt(plan_path: Path, spec_path: Path, work_id: str) -> str:
    return f"""You are working on NovelGuard.

/grill-with-docs

Goal:
Review the Plan card against the approved Spec before Todo/Scheduled.

Rules:
- Follow AGENTS.md and docs/agent/KANBAN-detail.md.
- Planning only. Do not edit product code under src/ or web/.
- Edit only this target card: {rel_path(plan_path)}
- Read approved spec: {rel_path(spec_path)}
- Fill Plan Gap Table on the plan card.

Inputs:
- work_id: {work_id}

Write or update on the plan card:
- Plan Gap Table (spec requirement vs plan coverage)
- Internal review notes
- Set frontmatter approved=true only when plan covers spec acceptance
"""


def grill_spec(spec_path: Path) -> tuple[bool, list[str]]:
    meta, body = read_card(spec_path)
    blockers: list[str] = []
    required = [
        "## Problem",
        "## Goals",
        "## Non-goals",
        HEADING_ACCEPTANCE_CRITERIA,
        "## files_allowed proposal",
    ]
    for heading in required:
        if heading not in body:
            blockers.append(f"missing {heading}")
    if not meta.get("acceptance") and "Acceptance criteria" not in body:
        blockers.append("missing acceptance criteria")
    narrative = body
    for heading in ("## files_allowed proposal", "## files_allowed"):
        pattern = re.compile(rf"^##\s+{re.escape(heading.lstrip('#').strip())}\s*$", re.MULTILINE)
        match = pattern.search(narrative)
        if match:
            narrative = narrative[: match.start()]
    if "src/" in narrative or "web/" in narrative:
        blockers.append("spec review mentions product paths; human approval recommended")
    return not blockers, blockers


def _infer_start_from_todo(todo_path: Path | None) -> str | None:
    if not todo_path:
        return None
    _, todo_body = read_card(todo_path)
    if is_generic_todo_body(todo_body):
        return "todo"
    return None


def _infer_start_from_plan(plan_path: Path | None) -> str | None:
    if not plan_path:
        return None
    plan_meta, plan_body = read_card(plan_path)
    plan_status = normalize_column(str(plan_meta.get("status") or ""))
    if plan_meta.get("approved") and is_generic_plan_body(plan_body):
        return "enrich_plan"
    if plan_status == "plan-review" and not plan_meta.get("approved"):
        return "validate_plan"
    if plan_status in ("plan-review", "plan-draft") and plan_meta.get("approved"):
        return "todo"
    if plan_status == "plan-draft":
        return "enrich_plan"
    return None


def _infer_start_from_spec(spec_path: Path | None) -> str | None:
    if not spec_path:
        return None
    spec_meta, _ = read_card(spec_path)
    spec_status = normalize_column(str(spec_meta.get("status") or ""))
    if spec_status == "spec-review" and not spec_meta.get("approved"):
        return "validate_spec"
    if spec_status == "spec-review" and spec_meta.get("approved"):
        return "plan_draft"
    if spec_status == "spec-draft":
        return "enrich_spec"
    return None


def infer_pipeline_start(config: dict, work_id: str) -> tuple[str, Path | None, Path | None]:
    """Return (start_phase, spec_path, plan_path) for resuming inbox automation."""
    spec_path = find_card_for_stage(config, work_id, "spec-draft")
    plan_path = find_card_for_stage(config, work_id, "plan-draft")
    todo_path = find_card_for_stage(config, work_id, "todo")
    for phase in (
        _infer_start_from_todo(todo_path),
        _infer_start_from_plan(plan_path),
        _infer_start_from_spec(spec_path),
    ):
        if phase:
            return phase, spec_path, plan_path
    return "inbox", spec_path, plan_path


def review_settings(config: dict) -> dict:
    mode = str(config.get("review_mode", "normal")).lower()
    if mode not in ("fast", "normal", "strict"):
        mode = "normal"
    cursor_grill = mode == "strict" or bool(config.get("cursor_grill", False))
    return {
        "mode": mode,
        "cursor_planning": bool(config.get("cursor_planning", mode != "fast")),
        "cursor_grill": cursor_grill,
        "cursor_todo": bool(config.get("cursor_todo", False)),
        "grill_on_blocker_only": bool(config.get("grill_on_blocker_only", True)),
    }


def min_plan_tasks(settings: dict) -> int:
    return 1 if settings["mode"] == "fast" else 3


def grill_plan(plan_path: Path, spec_path: Path, *, min_tasks: int = 3, check_generic: bool = True) -> tuple[bool, list[str]]:
    _, plan_body = read_card(plan_path)
    _, spec_body = read_card(spec_path)
    blockers: list[str] = []
    for heading in (
        HEADING_IMPLEMENTATION_TASKS,
        "## Verification matrix",
        "## Rollback plan",
        "## Branch name",
    ):
        if heading not in plan_body:
            blockers.append(f"missing {heading}")
    if "Acceptance criteria" in spec_body and "Verification matrix" not in plan_body:
        blockers.append("plan does not cover acceptance criteria")
    if check_generic and is_generic_plan_body(plan_body):
        blockers.append("plan still contains automation placeholder tasks")
    tasks = extract_bullets(plan_body, SECTION_IMPLEMENTATION_TASKS)
    if len(tasks) < min_tasks:
        blockers.append(f"implementation tasks too thin (need at least {min_tasks} step(s))")
    return not blockers, blockers


def validate_plan_fast(plan_path: Path) -> tuple[bool, list[str]]:
    _, plan_body = read_card(plan_path)
    blockers: list[str] = []
    if HEADING_IMPLEMENTATION_TASKS not in plan_body:
        blockers.append(f"missing {SECTION_IMPLEMENTATION_TASKS}")
    tasks = extract_bullets(plan_body, SECTION_IMPLEMENTATION_TASKS)
    if not tasks:
        blockers.append("need at least one implementation task")
    if "## Verification matrix" not in plan_body:
        blockers.append("missing Verification matrix")
    elif not re.search(r"`[^`]+`|pytest|npm run", plan_body, re.IGNORECASE):
        blockers.append("verification matrix missing a concrete command")
    return not blockers, blockers


def validate_spec_fast(spec_path: Path, allowed: list[str]) -> tuple[bool, list[str]]:
    meta, body = read_card(spec_path)
    blockers: list[str] = []
    if not meta.get("acceptance") and "acceptance" not in body.lower():
        blockers.append("missing acceptance")
    if not allowed and "## files_allowed" not in body.lower():
        blockers.append("missing files_allowed")
    return not blockers, blockers


def build_spec_template(body: str, meta: dict, allowed: list[str]) -> str:
    return f"""
## Problem

{body.strip()[:1200] or "Define the product problem from the inbox card."}

## Goals

- Preserve the requested behavior.
- Keep changes inside the declared files_allowed boundary.

## Non-goals

- No product-code implementation during planning automation.
- No deletion of Inbox, Spec, Plan, or Todo audit cards.

## Decisions

- Use local-only Kanban automation.
- Keep Ready/Ready Gate behavior as gate-check only.

## UX impact

- To be confirmed against acceptance before implementation.

## Backend impact

- To be confirmed against acceptance before implementation.

## Safety impact

- Product code is blocked until the Scheduled card moves to In Progress.

{HEADING_ACCEPTANCE_CRITERIA}

{meta.get("acceptance") or "- Acceptance must match the source Inbox card."}

## files_allowed proposal

{chr(10).join(f"- {item}" for item in allowed)}
"""


def build_plan_template(spec_path: Path, work_id: str, allowed: list[str]) -> str:
    return f"""
## Spec link

- {rel_path(spec_path)}

{HEADING_IMPLEMENTATION_TASKS}

- Implement the approved acceptance criteria inside files_allowed only.
- Record changed paths and verification commands.

## Files allowed

{chr(10).join(f"- {item}" for item in allowed)}

## Verification matrix

- `python scripts/verify_phase_completion.py` if present.
- Targeted tests listed by the implementation card or plan.

## Risks

- Scope creep outside files_allowed.
- Missing evidence for verification.

## Rollback plan

- Revert only changed files for this work item after human review.

## Branch name

- `feat/{work_id}`
"""


def build_todo_from_spec(spec_path: Path, allowed: list[str]) -> str:
    """Build checklist from spec scope when plan tasks are still placeholders."""
    _, spec_body = read_card(spec_path)
    scope_lines = extract_bullets(spec_body, "Scope")
    scope_text = " ".join(scope_lines) if scope_lines else spec_body
    tasks: list[str] = []
    if "exact" in scope_text.lower() or "duplicate" in scope_text.lower():
        tasks = [
            "Reproduce: scan byte-identical files, approve exact duplicate group in Resolve, run preview then apply; capture current keeper vs move_duplicate row state",
            "Trace approve → review_state_merge → reconcile_approved_duplicate_proposed_actions; fix stale all-keep or missing move_duplicate on non-keepers (`src/application/review_state_merge.py`, `src/application/review_move_targets.py`)",
            "Ensure build_preview_plan selects approved non-keeper exact rows for move_duplicate to duplicate/ (`src/app/build_preview_plan.py`, `src/application/review_move_targets.py`)",
            "Verify Resolve grid shows keep vs move_duplicate consistently after reload (`web/src/` review UI + bridge contract as needed)",
            "Add regression test: approve → preview → apply; keeper stays on disk, non-keepers under duplicate/ (`tests/` bridge or kiwi e2e)",
        ]
    if not tasks:
        acceptance = ""
        if HEADING_ACCEPTANCE_CRITERIA in spec_body:
            acceptance = (
                spec_body.split(HEADING_ACCEPTANCE_CRITERIA, 1)[1].split("##", 1)[0].strip()[:200]
            )
        tasks = [
            f"Implement acceptance: {acceptance or 'see spec card'}",
            "Run targeted verification and record changed paths",
        ]
    lines = ["## Checklist", ""]
    for index, task in enumerate(tasks, start=1):
        verify = (
            "`pytest tests/ -k exact -v`"
            if index == len(tasks) and "test" in task.lower()
            else "`python scripts/verify_phase_completion.py`"
        )
        lines.extend(
            [
                f"- [ ] T{index}",
                f"  - task: {task}",
                f"  - files_allowed: {', '.join(allowed)}",
                f"  - expected verification: {verify}",
                "  - risk: scope outside files_allowed for this chunk",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def build_todo_content(plan_path: Path | None, spec_path: Path, allowed: list[str]) -> str | None:
    if plan_path and plan_path.exists():
        _, plan_body = read_card(plan_path)
        if not is_generic_plan_body(plan_body):
            content = build_todo_from_plan(plan_path, allowed)
            if content:
                return content
    return build_todo_from_spec(spec_path, allowed)


def build_todo_from_plan(plan_path: Path, allowed: list[str]) -> str | None:
    _, plan_body = read_card(plan_path)
    tasks = extract_bullets(plan_body, SECTION_IMPLEMENTATION_TASKS)
    if not tasks:
        return None
    lines = ["## Checklist", ""]
    verification = "`python scripts/verify_phase_completion.py` if present"
    for index, task in enumerate(tasks, start=1):
        lines.extend(
            [
                f"- [ ] T{index}",
                f"  - task: {task}",
                f"  - files_allowed: {', '.join(allowed)}",
                f"  - expected verification: {verification}",
                "  - risk: scope outside files_allowed for this chunk",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def write_blocker_grill_prompt(
    config: dict,
    work_id: str,
    phase: str,
    prompt: str,
    *,
    dry_run: bool,
) -> Path:
    return write_prompt_file(config, work_id, f"{phase}-blocked", prompt, dry_run=dry_run)


def maybe_run_cursor_grill(
    config: dict,
    settings: dict,
    work_id: str,
    phase: str,
    prompt: str,
    *,
    dry_run: bool,
) -> tuple[Path | None, dict | None, str | None]:
    if not settings["cursor_grill"]:
        return None, None, None
    _step(work_id, f"{phase} Cursor grill (strict mode)")
    return run_cursor_phase(config, work_id, phase, prompt, dry_run=dry_run)


def grill_todo(todo_path: Path, plan_path: Path, *, min_items: int = 1) -> tuple[bool, list[str]]:
    _, todo_body = read_card(todo_path)
    _, plan_body = read_card(plan_path)
    blockers: list[str] = []
    if is_generic_todo_body(todo_body):
        blockers.append("todo checklist still placeholder (T1 only)")
    checklist = [line for line in todo_body.splitlines() if line.strip().startswith("- [ ]")]
    plan_tasks = extract_bullets(plan_body, SECTION_IMPLEMENTATION_TASKS)
    if plan_tasks and len(checklist) < min(min_items, len(plan_tasks)):
        blockers.append("todo checklist has fewer items than plan tasks")
    if "expected verification" not in todo_body.lower():
        blockers.append("todo items missing expected verification")
    return not blockers, blockers


def finalize_scheduled(
    card_path: Path,
    config: dict,
    state: dict,
    work_id: str,
    meta: dict,
    allowed: list[str],
    spec_path: Path,
    plan_path: Path,
    todo_path: Path,
    *,
    dry_run: bool,
    start_column: str,
    changed_paths: list[str],
) -> dict:
    scheduled_body = f"""
## Links

- Inbox: {rel_path(card_path)}
- Spec: {rel_path(spec_path)}
- Plan: {rel_path(plan_path)}
- Todo: {rel_path(todo_path)}

## Acceptance

{meta.get("acceptance") or "See linked Inbox and Spec."}

## files_allowed

{chr(10).join(f"- {item}" for item in allowed)}

## Branch

- `feat/{work_id}`
"""
    scheduled_path = create_card_if_missing(
        config,
        "scheduled",
        work_id,
        f"[Scheduled] {work_id}",
        {
            "linked_inbox": rel_path(card_path),
            "linked_spec": rel_path(spec_path),
            "linked_plan": rel_path(plan_path),
            "linked_todo": rel_path(todo_path),
            "files_allowed": allowed,
            "acceptance": meta.get("acceptance") or "See linked Inbox and Spec.",
            "branch": f"feat/{work_id}",
        },
        scheduled_body,
        dry_run=dry_run,
    )
    changed_paths.append(rel_path(scheduled_path))
    update_frontmatter(
        card_path,
        {
            "automation_state": "consumed",
            "linked_scheduled": rel_path(scheduled_path),
            "lifecycle": "consumed-inbox",
        },
        dry_run=dry_run,
    )
    archived_inbox = move_card(card_path, "done", config, dry_run=dry_run)
    changed_paths.append(rel_path(archived_inbox))
    state[f"{work_id}:scheduled-created"] = True
    _step(work_id, f"scheduled card ready -> {rel_path(scheduled_path)}")
    _step(work_id, f"inbox archived -> {rel_path(archived_inbox)} (leaves Inbox column)")
    run_sync_kanban_folders_if_present(dry_run=dry_run)
    return {
        "work_id": work_id,
        "status": "OK",
        "start_column": start_column,
        "end_column": "scheduled",
        "changed_paths": changed_paths,
        "blockers": [],
        "next_action": "run scheduled-to-in-progress automation after human approval",
    }


def ensure_todo_card(
    config: dict,
    settings: dict,
    state: dict,
    work_id: str,
    card_path: Path,
    spec_path: Path,
    plan_path: Path,
    allowed: list[str],
    *,
    dry_run: bool,
) -> tuple[Path | None, list[str], list[str]]:
    changed: list[str] = []
    blockers: list[str] = []
    todo_path = find_card_for_stage(config, work_id, "todo")
    if todo_path and not is_generic_todo_body(read_card(todo_path)[1]):
        _step(work_id, "todo checklist already populated; skipping regeneration")
        return todo_path, blockers, changed

    todo_content = build_todo_content(plan_path if plan_path else None, spec_path, allowed)

    if todo_content and not settings["cursor_todo"]:
        if not todo_path:
            todo_path = create_card_if_missing(
                config,
                "todo",
                work_id,
                f"[Todo] {work_id}",
                {
                    "linked_inbox": rel_path(card_path),
                    "linked_spec": rel_path(spec_path),
                    "linked_plan": rel_path(plan_path),
                    "files_allowed": allowed,
                },
                todo_content,
                dry_run=dry_run,
            )
            changed.append(rel_path(todo_path))
            state[f"{work_id}:todo-created"] = True
        else:
            meta, _ = read_card(todo_path)
            write_card(todo_path, meta, f"# [Todo] {work_id}\n\n{todo_content}", dry_run=dry_run)
            changed.append(rel_path(todo_path))
        _step(work_id, "todo checklist generated (deterministic from plan or spec)")
        return todo_path, blockers, changed

    if not todo_path:
        todo_path = create_card_if_missing(
            config,
            "todo",
            work_id,
            f"[Todo] {work_id}",
            {
                "linked_inbox": rel_path(card_path),
                "linked_spec": rel_path(spec_path),
                "linked_plan": rel_path(plan_path),
                "files_allowed": allowed,
            },
            "## Checklist\n\n- [ ] T1 (placeholder)\n",
            dry_run=dry_run,
        )
        changed.append(rel_path(todo_path))
        state[f"{work_id}:todo-created"] = True

    if settings["cursor_todo"] or not todo_content:
        _step(work_id, "todo-checklist phase (Cursor CLI fallback)")
        todo_prompt = build_todo_prompt(plan_path, spec_path, todo_path, work_id, allowed)
        prompt_path, cursor_result, cursor_blocker = run_cursor_phase(
            config,
            work_id,
            "todo-checklist",
            todo_prompt,
            dry_run=dry_run,
        )
        changed.append(rel_path(prompt_path))
        if cursor_result:
            state[f"{work_id}:todo-checklist-cursor-exit-code"] = cursor_result["exit_code"]
        if cursor_blocker:
            blockers.append(cursor_blocker)

    return todo_path, blockers, changed


def _scheduled_preflight(
    config: dict, work_id: str, start_column: str, card_path: Path
) -> dict | None:
    scheduled_path, scheduled_blocker = ensure_unique_card(config, "scheduled", work_id)
    if scheduled_blocker:
        return _blocked(
            work_id,
            start_column=start_column,
            end_column=start_column,
            changed_paths=[rel_path(card_path)],
            blockers=[scheduled_blocker],
            next_action="deduplicate scheduled cards",
        )
    if scheduled_path:
        return _pipeline_result(
            work_id,
            status="IDLE",
            start_column=start_column,
            end_column="scheduled",
            changed_paths=[],
            next_action=(
                "already scheduled; run scheduled-to-in-progress automation after human approval"
            ),
        )
    return None


def _collect_inbox_gate_blockers(
    card_path: Path, meta: dict, body: str, config: dict
) -> list[str]:
    blockers: list[str] = []
    drift = detect_drift(card_path, config)
    if drift:
        blockers.append(drift)
    if not has_acceptance(meta, body):
        blockers.append("missing acceptance")
    if not files_allowed(meta, body):
        blockers.append("missing files_allowed")
    return blockers


def _normalize_inbox_card(
    card_path: Path,
    meta: dict,
    work_id: str,
    allowed: list[str],
    changed_paths: list[str],
    *,
    dry_run: bool,
) -> None:
    if str(meta.get("automation_state") or "").lower() == "inbox_normalized":
        return
    update_frontmatter(
        card_path,
        {
            "work_id": work_id,
            "files_allowed": allowed,
            "automation_state": "inbox_normalized",
        },
        dry_run=dry_run,
    )
    changed_paths.append(rel_path(card_path))


def _ensure_spec_draft(
    card_path: Path,
    config: dict,
    state: dict,
    meta: dict,
    body: str,
    work_id: str,
    allowed: list[str],
    settings: dict,
    start_phase: str,
    spec_path: Path | None,
    changed_paths: list[str],
    *,
    dry_run: bool,
) -> tuple[Path | None, str]:
    if start_phase != "inbox" and spec_path:
        return spec_path, start_phase
    _step(work_id, "creating spec-draft")
    spec_path = create_card_if_missing(
        config,
        "spec-draft",
        work_id,
        f"[Spec Draft] {work_id}",
        {
            "linked_inbox": rel_path(card_path),
            "acceptance": meta.get("acceptance") or INBOX_ACCEPTANCE_FALLBACK,
            "files_allowed": allowed,
        },
        build_spec_template(body, meta, allowed),
        dry_run=dry_run,
    )
    changed_paths.append(rel_path(spec_path))
    state[f"{work_id}:spec-draft-created"] = True
    next_phase = "enrich_spec" if settings["cursor_planning"] else "validate_spec"
    return spec_path, next_phase


def _run_spec_cursor_enrich(
    card_path: Path,
    spec_path: Path,
    config: dict,
    state: dict,
    meta: dict,
    body: str,
    work_id: str,
    allowed: list[str],
    start_phase: str,
    settings: dict,
    start_column: str,
    changed_paths: list[str],
    *,
    dry_run: bool,
) -> dict | None:
    if start_phase != "enrich_spec":
        return None
    if not settings["cursor_planning"]:
        _step(work_id, "skip spec Cursor planning (cursor_planning=false)")
        return None
    _step(work_id, "brainstorming phase (Cursor planning)")
    brainstorming_prompt = build_brainstorming_prompt(
        card_path,
        spec_path,
        work_id,
        allowed,
        _inbox_acceptance_from(meta),
        body,
    )
    prompt_path, cursor_result, cursor_blocker = run_cursor_phase(
        config, work_id, "brainstorming", brainstorming_prompt, dry_run=dry_run,
    )
    changed_paths.append(rel_path(prompt_path))
    if cursor_result:
        state[f"{work_id}:brainstorming-cursor-exit-code"] = cursor_result["exit_code"]
    if not cursor_blocker:
        return None
    append_cursor_blocked_feedback(spec_path, prompt_path, cursor_blocker, dry_run=dry_run)
    return _blocked(
        work_id,
        start_column=start_column,
        end_column="spec-draft",
        changed_paths=changed_paths,
        blockers=[cursor_blocker],
        next_action="run /brainstorming prompt with Cursor CLI",
    )


def _move_spec_to_review(
    spec_path: Path, config: dict, changed_paths: list[str], *, dry_run: bool
) -> tuple[Path, dict]:
    spec_meta, _ = read_card(spec_path)
    if normalize_column(str(spec_meta.get("status") or "")) == "spec-review":
        return spec_path, spec_meta
    spec_path = move_card(spec_path, "spec-review", config, dry_run=dry_run)
    changed_paths.append(rel_path(spec_path))
    spec_meta, _ = read_card(spec_path)
    return spec_path, spec_meta


def _validate_spec_card(
    card_path: Path,
    spec_path: Path,
    config: dict,
    state: dict,
    settings: dict,
    work_id: str,
    start_column: str,
    changed_paths: list[str],
    *,
    dry_run: bool,
) -> dict | None:
    spec_meta, _ = read_card(spec_path)
    if spec_meta.get("approved"):
        return None
    _step(work_id, "local spec validation")
    if settings["cursor_grill"]:
        grill_prompt = build_grill_spec_prompt(spec_path, card_path, work_id)
        prompt_path, cursor_result, cursor_blocker = maybe_run_cursor_grill(
            config, settings, work_id, "grill-spec", grill_prompt, dry_run=dry_run,
        )
        if prompt_path:
            changed_paths.append(rel_path(prompt_path))
        if cursor_result:
            state[f"{work_id}:grill-spec-cursor-exit-code"] = cursor_result["exit_code"]
        if cursor_blocker:
            append_cursor_blocked_feedback(spec_path, prompt_path, cursor_blocker, dry_run=dry_run)
            return _blocked(
                work_id,
                start_column=start_column,
                end_column="spec-review",
                changed_paths=changed_paths,
                blockers=[cursor_blocker],
                next_action="resolve spec grill failure",
            )
    spec_ok, spec_blockers = grill_spec(spec_path)
    if not spec_ok:
        if settings["grill_on_blocker_only"]:
            blocked_prompt = write_blocker_grill_prompt(
                config, work_id, "grill-spec", build_grill_spec_prompt(spec_path, card_path, work_id), dry_run=dry_run,
            )
            changed_paths.append(rel_path(blocked_prompt))
            _step(work_id, "grill-spec prompt saved for manual/strict review")
        append_card_section(
            spec_path,
            "Internal Grill Review",
            [f"- BLOCKED: {item}" for item in spec_blockers],
            dry_run=dry_run,
        )
        return _blocked(
            work_id,
            start_column=start_column,
            end_column="spec-review",
            changed_paths=changed_paths,
            blockers=spec_blockers,
            next_action="resolve spec review gaps",
        )
    update_frontmatter(
        spec_path,
        {"approved": True, "approved_by": "kanban_automation", "approved_at": "auto", "automation_state": "approved"},
        dry_run=dry_run,
    )
    append_card_section(spec_path, "Internal Grill Review", ["- Local validation passed."], dry_run=dry_run)
    return None


def _ensure_plan_draft(
    card_path: Path,
    config: dict,
    state: dict,
    work_id: str,
    allowed: list[str],
    spec_path: Path,
    settings: dict,
    start_phase: str,
    plan_path: Path | None,
    changed_paths: list[str],
    *,
    dry_run: bool,
) -> tuple[Path | None, str]:
    if plan_path and start_phase != "plan_draft":
        return plan_path, start_phase
    _step(work_id, "creating plan-draft")
    plan_path = create_card_if_missing(
        config,
        "plan-draft",
        work_id,
        f"[Plan Draft] {work_id}",
        {
            "linked_inbox": rel_path(card_path),
            "linked_spec": rel_path(spec_path),
            "files_allowed": allowed,
            "branch": f"feat/{work_id}",
        },
        build_plan_template(spec_path, work_id, allowed),
        dry_run=dry_run,
    )
    changed_paths.append(rel_path(plan_path))
    state[f"{work_id}:plan-draft-created"] = True
    next_phase = "enrich_plan" if settings["cursor_planning"] else "validate_plan"
    return plan_path, next_phase


def _run_plan_cursor_enrich(
    plan_path: Path,
    spec_path: Path,
    config: dict,
    state: dict,
    work_id: str,
    allowed: list[str],
    start_phase: str,
    settings: dict,
    start_column: str,
    changed_paths: list[str],
    *,
    dry_run: bool,
) -> tuple[Path, dict | None]:
    if start_phase != "enrich_plan":
        return plan_path, None
    if not settings["cursor_planning"]:
        _step(work_id, "skip plan Cursor planning (cursor_planning=false)")
        return plan_path, None
    _, plan_body = read_card(plan_path)
    if is_generic_plan_body(plan_body):
        plan_path = reset_plan_for_rework(plan_path, config, dry_run=dry_run)
        changed_paths.append(rel_path(plan_path))
    _step(work_id, "writing-plans phase (Cursor planning)")
    writing_plans_prompt = build_writing_plans_prompt(spec_path, plan_path, work_id, allowed, f"feat/{work_id}")
    prompt_path, cursor_result, cursor_blocker = run_cursor_phase(
        config, work_id, "writing-plans", writing_plans_prompt, dry_run=dry_run,
    )
    changed_paths.append(rel_path(prompt_path))
    if cursor_result:
        state[f"{work_id}:writing-plans-cursor-exit-code"] = cursor_result["exit_code"]
    if not cursor_blocker:
        return plan_path, None
    append_cursor_blocked_feedback(plan_path, prompt_path, cursor_blocker, dry_run=dry_run)
    return plan_path, _blocked(
        work_id,
        start_column=start_column,
        end_column="plan-draft",
        changed_paths=changed_paths,
        blockers=[cursor_blocker],
        next_action="run /writing-plans prompt with Cursor CLI",
    )


def _move_plan_to_review(
    plan_path: Path, config: dict, changed_paths: list[str], *, dry_run: bool
) -> tuple[Path, dict, str]:
    plan_meta, plan_body = read_card(plan_path)
    if normalize_column(str(plan_meta.get("status") or "")) != "plan-review":
        plan_path = move_card(plan_path, "plan-review", config, dry_run=dry_run)
        changed_paths.append(rel_path(plan_path))
        plan_meta, plan_body = read_card(plan_path)
    return plan_path, plan_meta, plan_body


def _validate_plan_card(
    plan_path: Path,
    spec_path: Path,
    config: dict,
    state: dict,
    settings: dict,
    work_id: str,
    start_column: str,
    changed_paths: list[str],
    *,
    dry_run: bool,
) -> dict | None:
    plan_meta, _ = read_card(plan_path)
    if plan_meta.get("approved"):
        return None
    _step(work_id, "local plan validation")
    if settings["cursor_grill"]:
        grill_prompt = build_grill_plan_prompt(plan_path, spec_path, work_id)
        prompt_path, cursor_result, cursor_blocker = maybe_run_cursor_grill(
            config, settings, work_id, "grill-plan", grill_prompt, dry_run=dry_run,
        )
        if prompt_path:
            changed_paths.append(rel_path(prompt_path))
        if cursor_result:
            state[f"{work_id}:grill-plan-cursor-exit-code"] = cursor_result["exit_code"]
        if cursor_blocker:
            append_cursor_blocked_feedback(plan_path, prompt_path, cursor_blocker, dry_run=dry_run)
            return _blocked(
                work_id,
                start_column=start_column,
                end_column="plan-review",
                changed_paths=changed_paths,
                blockers=[cursor_blocker],
                next_action="resolve plan grill failure",
            )
    plan_ok, plan_blockers = grill_plan(
        plan_path, spec_path, min_tasks=min_plan_tasks(settings), check_generic=True,
    )
    append_card_section(
        plan_path,
        "Plan Gap Table",
        [
            "| Spec requirement | Plan coverage | Status | Fix |",
            "|---|---|---|---|",
            "| Acceptance criteria | Verification matrix | pass | none |"
            if plan_ok
            else "| Acceptance criteria | incomplete | blocked | add missing coverage |",
        ],
        dry_run=dry_run,
    )
    if not plan_ok:
        if settings["grill_on_blocker_only"]:
            blocked_prompt = write_blocker_grill_prompt(
                config, work_id, "grill-plan", build_grill_plan_prompt(plan_path, spec_path, work_id), dry_run=dry_run,
            )
            changed_paths.append(rel_path(blocked_prompt))
            _step(work_id, "grill-plan prompt saved for manual/strict review")
        return _blocked(
            work_id,
            start_column=start_column,
            end_column="plan-review",
            changed_paths=changed_paths,
            blockers=plan_blockers,
            next_action="resolve plan review gaps",
        )
    update_frontmatter(
        plan_path,
        {"approved": True, "approved_by": "kanban_automation", "approved_at": "auto", "automation_state": "approved"},
        dry_run=dry_run,
    )
    return None


def _finalize_todo_and_schedule(
    card_path: Path,
    config: dict,
    state: dict,
    meta: dict,
    work_id: str,
    allowed: list[str],
    spec_path: Path,
    plan_path: Path,
    settings: dict,
    start_column: str,
    changed_paths: list[str],
    *,
    dry_run: bool,
) -> dict:
    todo_path, todo_blockers, todo_changed = ensure_todo_card(
        config, settings, state, work_id, card_path, spec_path, plan_path, allowed, dry_run=dry_run,
    )
    changed_paths.extend(todo_changed)
    if todo_blockers:
        return _blocked(
            work_id,
            start_column=start_column,
            end_column="todo",
            changed_paths=changed_paths,
            blockers=todo_blockers,
            next_action="resolve todo checklist gaps",
        )
    if not todo_path:
        return _blocked(
            work_id,
            start_column=start_column,
            end_column="todo",
            changed_paths=changed_paths,
            blockers=["missing todo card"],
            next_action="create todo card",
        )
    todo_ok, todo_blockers = grill_todo(todo_path, plan_path, min_items=1)
    if not todo_ok:
        append_blocked_feedback(todo_path, todo_blockers, dry_run=dry_run)
        return _blocked(
            work_id,
            start_column=start_column,
            end_column="todo",
            changed_paths=changed_paths,
            blockers=todo_blockers,
            next_action="resolve todo checklist gaps",
        )
    return finalize_scheduled(
        card_path, config, state, work_id, meta, allowed, spec_path, plan_path, todo_path,
        dry_run=dry_run, start_column=start_column, changed_paths=changed_paths,
    )


def _process_inbox_normal_pipeline(
    card_path: Path,
    config: dict,
    state: dict,
    meta: dict,
    body: str,
    work_id: str,
    allowed: list[str],
    settings: dict,
    *,
    dry_run: bool,
    start_column: str,
    changed_paths: list[str],
) -> dict:
    start_phase, existing_spec_path, existing_plan_path = infer_pipeline_start(config, work_id)
    if start_phase != "inbox":
        _step(work_id, f"resume pipeline at {start_phase}")

    spec_path, start_phase = _ensure_spec_draft(
        card_path, config, state, meta, body, work_id, allowed, settings,
        start_phase, existing_spec_path, changed_paths, dry_run=dry_run,
    )
    if not spec_path:
        return _blocked(
            work_id,
            start_column=start_column,
            end_column=start_column,
            changed_paths=changed_paths,
            blockers=["missing spec card for resume"],
            next_action="restore or recreate spec card",
        )

    if blocked := _run_spec_cursor_enrich(
        card_path, spec_path, config, state, meta, body, work_id, allowed,
        start_phase, settings, start_column, changed_paths, dry_run=dry_run,
    ):
        return blocked

    spec_path, _ = _move_spec_to_review(spec_path, config, changed_paths, dry_run=dry_run)
    if blocked := _validate_spec_card(
        card_path, spec_path, config, state, settings, work_id, start_column, changed_paths, dry_run=dry_run,
    ):
        return blocked

    plan_path, start_phase = _ensure_plan_draft(
        card_path, config, state, work_id, allowed, spec_path, settings,
        start_phase, existing_plan_path, changed_paths, dry_run=dry_run,
    )
    if not plan_path:
        return _blocked(
            work_id,
            start_column=start_column,
            end_column="plan-draft",
            changed_paths=changed_paths,
            blockers=["missing plan card for resume"],
            next_action="restore or recreate plan card",
        )

    plan_path, blocked = _run_plan_cursor_enrich(
        plan_path, spec_path, config, state, work_id, allowed,
        start_phase, settings, start_column, changed_paths, dry_run=dry_run,
    )
    if blocked:
        return blocked

    plan_path, _, _ = _move_plan_to_review(plan_path, config, changed_paths, dry_run=dry_run)
    if blocked := _validate_plan_card(
        plan_path, spec_path, config, state, settings, work_id, start_column, changed_paths, dry_run=dry_run,
    ):
        return blocked

    return _finalize_todo_and_schedule(
        card_path, config, state, meta, work_id, allowed, spec_path, plan_path, settings,
        start_column, changed_paths, dry_run=dry_run,
    )


def process_inbox_card_fast(
    card_path: Path,
    config: dict,
    state: dict,
    meta: dict,
    body: str,
    work_id: str,
    allowed: list[str],
    *,
    dry_run: bool,
    start_column: str,
    changed_paths: list[str],
) -> dict:
    _step(work_id, "fast mode: template bundle + minimal validation")
    spec_path = create_card_if_missing(
        config,
        "spec-draft",
        work_id,
        f"[Spec Draft] {work_id}",
        {
            "linked_inbox": rel_path(card_path),
            "acceptance": meta.get("acceptance") or INBOX_ACCEPTANCE_FALLBACK,
            "files_allowed": allowed,
        },
        build_spec_template(body, meta, allowed),
        dry_run=dry_run,
    )
    changed_paths.append(rel_path(spec_path))
    spec_path = move_card(spec_path, "spec-review", config, dry_run=dry_run)
    changed_paths.append(rel_path(spec_path))

    spec_ok, spec_blockers = validate_spec_fast(spec_path, allowed)
    if not spec_ok:
        append_blocked_feedback(spec_path, spec_blockers, dry_run=dry_run)
        return _blocked(
            work_id,
            start_column=start_column,
            end_column="spec-review",
            changed_paths=changed_paths,
            blockers=spec_blockers,
            next_action="fix spec for fast mode",
        )
    update_frontmatter(
        spec_path,
        {"approved": True, "approved_by": "kanban_automation", "approved_at": "auto", "automation_state": "approved"},
        dry_run=dry_run,
    )

    plan_path = create_card_if_missing(
        config,
        "plan-draft",
        work_id,
        f"[Plan Draft] {work_id}",
        {
            "linked_inbox": rel_path(card_path),
            "linked_spec": rel_path(spec_path),
            "files_allowed": allowed,
            "branch": f"feat/{work_id}",
        },
        build_plan_template(spec_path, work_id, allowed),
        dry_run=dry_run,
    )
    changed_paths.append(rel_path(plan_path))
    plan_path = move_card(plan_path, "plan-review", config, dry_run=dry_run)
    changed_paths.append(rel_path(plan_path))

    plan_ok, plan_blockers = validate_plan_fast(plan_path)
    if not plan_ok:
        append_blocked_feedback(plan_path, plan_blockers, dry_run=dry_run)
        return _blocked(
            work_id,
            start_column=start_column,
            end_column="plan-review",
            changed_paths=changed_paths,
            blockers=plan_blockers,
            next_action="fix plan for fast mode",
        )
    update_frontmatter(
        plan_path,
        {"approved": True, "approved_by": "kanban_automation", "approved_at": "auto", "automation_state": "approved"},
        dry_run=dry_run,
    )

    settings = review_settings(config)
    todo_path, todo_blockers, todo_changed = ensure_todo_card(
        config, settings, state, work_id, card_path, spec_path, plan_path, allowed, dry_run=dry_run,
    )
    changed_paths.extend(todo_changed)
    if todo_blockers or not todo_path:
        return _blocked(
            work_id,
            start_column=start_column,
            end_column="todo",
            changed_paths=changed_paths,
            blockers=todo_blockers or ["missing todo card"],
            next_action="fix todo for fast mode",
        )

    return finalize_scheduled(
        card_path, config, state, work_id, meta, allowed, spec_path, plan_path, todo_path,
        dry_run=dry_run, start_column=start_column, changed_paths=changed_paths,
    )


def process_inbox_card(card_path: Path, config: dict, state: dict, *, dry_run: bool) -> dict:
    run_sync_kanban_folders_if_present(dry_run=dry_run)
    meta, body = read_card(card_path)
    work_id = normalize_work_id(str(meta.get("work_id") or meta.get("epic") or meta.get("id")), card_path.stem)
    _step(work_id, f"process inbox card {rel_path(card_path)}")
    changed_paths: list[str] = []
    start_column = "inbox"

    if preflight := _scheduled_preflight(config, work_id, start_column, card_path):
        return preflight

    blockers = _collect_inbox_gate_blockers(card_path, meta, body, config)
    if blockers:
        _step(work_id, f"inbox gate BLOCKED: {'; '.join(blockers)}")
        append_blocked_feedback(card_path, blockers, dry_run=dry_run)
        return _blocked(
            work_id,
            start_column=start_column,
            end_column=start_column,
            changed_paths=[rel_path(card_path)],
            blockers=blockers,
            next_action="fix inbox metadata",
        )

    allowed = files_allowed(meta, body)
    settings = review_settings(config)
    _step(work_id, f"review_mode={settings['mode']}")
    _normalize_inbox_card(card_path, meta, work_id, allowed, changed_paths, dry_run=dry_run)

    if settings["mode"] == "fast":
        return process_inbox_card_fast(
            card_path, config, state, meta, body, work_id, allowed,
            dry_run=dry_run, start_column=start_column, changed_paths=changed_paths,
        )

    return _process_inbox_normal_pipeline(
        card_path, config, state, meta, body, work_id, allowed, settings,
        dry_run=dry_run, start_column=start_column, changed_paths=changed_paths,
    )


def run_once(config: dict, state: dict, *, dry_run: bool) -> dict:
    inbox_cards = sorted(scan_cards(config, "inbox"), key=inbox_sort_key)
    terminal_log(
        f"inbox scan: {len(inbox_cards)} card(s)",
        script=SCRIPT_NAME,
        dedupe_key=f"{SCRIPT_NAME}:inbox_count",
    )
    if not inbox_cards:
        return {
            "work_id": "none",
            "status": "IDLE",
            "start_column": "inbox",
            "end_column": "inbox",
            "changed_paths": [],
            "blockers": [],
            "next_action": "no inbox cards found",
        }

    skipped: list[str] = []
    for card_path in inbox_cards:
        skip = inbox_skip_reason(card_path, config)
        if skip:
            meta, _ = read_card(card_path)
            work_id = normalize_work_id(str(meta.get("work_id") or meta.get("epic") or meta.get("id")), card_path.stem)
            skipped.append(f"{work_id} ({skip})")
            continue
        terminal_log(f"selected inbox card {rel_path(card_path)}", script=SCRIPT_NAME)
        result = process_inbox_card(card_path, config, state, dry_run=dry_run)
        pending = len(inbox_cards) - len(skipped) - 1
        if pending > 0 and result["status"] in ("OK", "BLOCKED", "FAILED"):
            result["next_action"] = f"{result['next_action']} ({pending} more inbox card(s) after this)"
        return result

    terminal_log(
        f"no actionable inbox ({len(inbox_cards)} total; skipped: {'; '.join(skipped) if skipped else 'none'})",
        script=SCRIPT_NAME,
        dedupe_key=f"{SCRIPT_NAME}:all_skipped",
    )
    return {
        "work_id": f"{len(inbox_cards)}-inbox",
        "status": "IDLE",
        "start_column": "inbox",
        "end_column": "inbox",
        "changed_paths": [],
        "blockers": [],
        "next_action": (
            f"no actionable inbox cards ({len(inbox_cards)} in inbox; "
            f"skipped: {'; '.join(skipped) if skipped else 'none'})"
        ),
    }


def main() -> int:
    parser = build_parser("Inbox to Scheduled Kanban automation")
    parser.add_argument(
        "--review-mode",
        choices=["fast", "normal", "strict"],
        help="Override review_mode from config (fast|normal|strict)",
    )
    args = parser.parse_args()
    config = load_config(args.config)
    if args.review_mode:
        config["review_mode"] = args.review_mode
    state = load_state(config)
    return run_automation_loop(
        SCRIPT_NAME,
        config,
        state,
        dry_run=args.dry_run,
        once=args.once,
        run_once_fn=run_once,
        sleep_seconds_fn=inbox_poll_sleep_seconds,
    )


if __name__ == "__main__":
    sys.exit(main())
