---
trigger: linear.labels@Todo
label: auto:grill-needs-revision
phase: revise-spec
project: NovelGuard
team: NovelGuard
repo: F:/Python_Projects/NovelGuard
commit: false
---

@docs/agents/runner-brief.md

# Todo → revise spec (grill blockers)

**Issue:** `{{ISSUE_IDENTIFIER}}` · **URL:** `{{ISSUE_URL}}` · **Job:** `{{JOB_ID}}`  
**HARD-GATE:** Linear MCP on **exactly** `{{ISSUE_IDENTIFIER}}` only.

**Entry:** Todo + `auto:grill-needs-revision` · **Exit:** Backlog + `auto:spec-done`

## Gate

| Check | Action |
| ----- | ------ |
| project/team ≠ NovelGuard | silent exit |
| status ≠ Todo | silent exit |
| missing `## Grill-me verdict` NEEDS_REVISION | silent exit |

**Never:** `src/`/`web/`/`tests/` edits, commit, branch, PR.

## Do

Fix grill blockers from verdict → `## Spec (revised)` (**Summary caveman** at top).

**Closeout — MUST** — `save_issue(state=Backlog, labels+=auto:spec-done)` **one call**. STOP. → `linear/backlog/grill-plan.md`.

**Tools:** Linear MCP · read-only repo
