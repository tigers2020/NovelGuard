<!-- legacy prompt path: prefer linear/todo/write-task-list.md -->

---
trigger: linear.labels@Todo
label: auto:plan-done
phase: write-task-list
project: NovelGuard
team: NovelGuard
repo: F:/Python_Projects/NovelGuard
commit: false
---

@docs/agents/runner-brief-compact.md

## Context memory
{{CONTEXT_MEMORY_JSON}}

# Todo → Task list → In Progress

**Issue:** `{{ISSUE_IDENTIFIER}}` · **URL:** `{{ISSUE_URL}}` · **Job:** `{{JOB_ID}}`  
**HARD-GATE:** Linear MCP on **exactly** `{{ISSUE_IDENTIFIER}}` only.

**Entry:** Todo + `auto:plan-done` · **Exit:** In Progress + `auto:task-list-done` (legacy `auto:todo-list-done` still routes)

## Gate

| Check | Action |
| ----- | ------ |
| project/team ≠ NovelGuard | silent exit |
| status ≠ Todo | silent exit |
| `auto:task-list-done` or `auto:todo-list-done` + no `regenerate task` | idempotent exit |
| missing Spec or Plan | silent exit |

**Never:** `src/`/`web/`/`tests/` edits, commit, branch, PR.

## Do

Need `## Spec` + `## Implementation Plan`. Post `## Task list` (**Summary caveman** at top).

Task list = bite-sized **implementation tasks** for `/subagent-driven-development` (one subagent per task; not a generic todo dump). Each row: checkbox, files, verify command, commit boundary.

**Closeout — MUST** — `save_issue(state=In Progress, labels+=auto:task-list-done)` **one call**. If label missing in workspace, use `auto:todo-list-done`. STOP. → `linear/in-progress/implement.md`.

**Tools:** Linear MCP · read-only repo
