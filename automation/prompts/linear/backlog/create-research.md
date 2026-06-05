---
trigger: linear.issue.created
phase: backlog-research
project: NovelGuard
team: NovelGuard
repo: F:/Python_Projects/NovelGuard
commit: false
base_branch: main
---

@docs/agents/runner-brief.md

# Backlog → research → branch

**Issue:** `{{ISSUE_IDENTIFIER}}` · **Exit:** Todo + `auto:research-done`

Research (read-only) → comment → feature branch. **No PR, no product edits.**

## Gate

| Check | Action |
| ----- | ------ |
| project/team ≠ NovelGuard | silent exit |
| status ≠ Backlog | silent exit |
| `## Research report` exists, no `regenerate` | idempotent exit |

**Never:** product code, commit (empty branch OK), grill / plans.

Progress labels (`triaging`, `researching`, `branch-creating`) — **no separate `save_issue`**. Closeout only.

## Do

1. **Load** — `get_issue` + `list_comments`. Parse Problem, AC, `files_allowed`.
2. **Research** — read-only `/caveman`; scoped `src/` / `web/` / `tests/`.  
   Blocked → `## Research blocked`, `auto:blocked`, Backlog, STOP.
3. **Comment** — `## Research report — {{ISSUE_IDENTIFIER}}`: **Summary (caveman)**, Problem, Root cause, Fix locations, AC, Verify commands, Risks.
4. **Branch** — `ai/{{ISSUE_IDENTIFIER}}-<slug>`: fetch, pull base, checkout -b, push -u. `## Branch ready` (name, base).
5. **Closeout — MUST** — `save_issue(state=Todo, labels+=auto:research-done)` **one call**. STOP. → `linear/todo/write-spec.md`.

**Tools:** Linear MCP · git (branch + push only)
