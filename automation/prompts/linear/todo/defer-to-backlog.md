---
trigger: linear.labels@Todo
label: auto:spec-done
phase: defer-to-backlog
project: NovelGuard
team: NovelGuard
repo: F:/Python_Projects/NovelGuard
commit: false
---

@docs/agents/runner-brief.md

# Todo → defer to Backlog (wrong state for grill)

**Issue:** `{{ISSUE_IDENTIFIER}}` · **URL:** `{{ISSUE_URL}}` · **Job:** `{{JOB_ID}}`  
**HARD-GATE:** Linear MCP on **exactly** `{{ISSUE_IDENTIFIER}}` only.

**Entry:** Todo + `auto:spec-done`, NOT `auto:plan-done` · **Exit:** Backlog (labels unchanged)

Phase 2 requires **Backlog**. Issue landed on Todo with spec only — move back, no new work.

## Gate

| Check | Action |
| ----- | ------ |
| status ≠ Todo | silent exit |
| `auto:plan-done` present | silent exit |
| status already Backlog | silent exit |

## Do

`save_issue(state=Backlog)` **only** — no label change. STOP. → `linear/backlog/grill-plan.md`.

**Tools:** Linear MCP only
