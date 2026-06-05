---
trigger: linear.labels@Backlog
label: auto:spec-done
phase: grill-plan
project: NovelGuard
team: NovelGuard
repo: F:/Python_Projects/NovelGuard
commit: false
---

@docs/agents/runner-brief.md

# Backlog → grill + plan

**Issue:** `{{ISSUE_IDENTIFIER}}` · **URL:** `{{ISSUE_URL}}` · **Job:** `{{JOB_ID}}`  
**HARD-GATE:** Linear MCP on **exactly** `{{ISSUE_IDENTIFIER}}` only.

**Entry:** Backlog + `auto:spec-done` · **Exit:** Todo + `auto:plan-done` | `auto:grill-needs-revision`

## Gate

| Check | Action |
| ----- | ------ |
| project/team ≠ NovelGuard | silent exit |
| status ≠ Backlog | silent exit |
| `auto:plan-done` + no `regenerate plan` | idempotent exit |

**Skip:** Plan + grill APPROVED already in comments → `save_issue(Todo, labels+=auto:plan-done)` **one call**. STOP. → `linear/todo/write-todo-list.md`.

**Never:** `src/`/`web/`/`tests/` edits, commit, branch, PR.

## Do

/grill-me · /writing-plans · read-only.

1. `## Grill-me verdict` (**Summary caveman**). NEEDS_REVISION → `save_issue(Todo, labels+=auto:grill-needs-revision)` **one call**. STOP. → `linear/todo/revise-spec.md`.
2. APPROVED → `## Implementation Plan` (**Summary caveman** at top) → `save_issue(Todo, labels+=auto:plan-done)` **one call**. STOP. → `linear/todo/write-todo-list.md`.

**Tools:** Linear MCP · read-only repo
