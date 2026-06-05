---
trigger: linear.labels@Todo
label: auto:plan-done
phase: write-todo-list
project: NovelGuard
team: NovelGuard
repo: F:/Python_Projects/NovelGuard
commit: false
---

@docs/agents/runner-brief-compact.md

## Context memory
{{CONTEXT_MEMORY_JSON}}

# Todo → todo list → In Progress

**Issue:** `{{ISSUE_IDENTIFIER}}` · **URL:** `{{ISSUE_URL}}` · **Job:** `{{JOB_ID}}`  
**HARD-GATE:** Linear MCP on **exactly** `{{ISSUE_IDENTIFIER}}` only.

**Entry:** Todo + `auto:plan-done` · **Exit:** In Progress + `auto:todo-list-done`

## Gate

| Check | Action |
| ----- | ------ |
| project/team ≠ NovelGuard | silent exit |
| status ≠ Todo | silent exit |
| `auto:todo-list-done` + no `regenerate todo` | idempotent exit |
| missing Spec or Plan | silent exit |

**Never:** `src/`/`web/`/`tests/` edits, commit, branch, PR.

## Do

Need `## Spec` + `## Implementation Plan`. Post `## Todo list` (**Summary caveman** at top).

**Closeout — MUST** — `save_issue(state=In Progress, labels+=auto:todo-list-done)` **one call**. STOP. → `linear/in-progress/implement.md`.

**Tools:** Linear MCP · read-only repo
