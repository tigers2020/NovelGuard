---
trigger: linear.labels@Todo
label: auto:research-done
phase: write-spec
project: NovelGuard
team: NovelGuard
repo: F:/Python_Projects/NovelGuard
commit: false
---

@docs/agents/runner-brief-compact.md

## Context memory
{{CONTEXT_MEMORY_JSON}}

# Todo → spec

**Issue:** `{{ISSUE_IDENTIFIER}}` · **URL:** `{{ISSUE_URL}}` · **Job:** `{{JOB_ID}}`  
**HARD-GATE:** Linear MCP on **exactly** `{{ISSUE_IDENTIFIER}}` only.

**Entry:** Todo + `auto:research-done` · **Exit:** Backlog + `auto:spec-done`

## Gate

| Check | Action |
| ----- | ------ |
| project/team ≠ NovelGuard | silent exit |
| status ≠ Todo | silent exit |
| `auto:spec-done` + no `regenerate spec` | idempotent exit |
| missing `## Research report` | silent exit |

**Skip:** Spec + brainstorm exist → `save_issue(Backlog, labels+=auto:spec-done)` **one call**. STOP. → `linear/backlog/grill-plan.md`.

`regenerate spec` disables skip.

**Never:** `src/`/`web/`/`tests/` edits, commit, branch, PR.

## Do

/brainstorming · read-only.

Post `## Brainstorm triage report` (**Summary caveman** + triage) + `## Spec` (**Summary caveman** at top).

**Closeout — MUST** — `save_issue(state=Backlog, labels+=auto:spec-done)` **one call**. STOP. → `linear/backlog/grill-plan.md`.

**Tools:** Linear MCP · read-only repo
