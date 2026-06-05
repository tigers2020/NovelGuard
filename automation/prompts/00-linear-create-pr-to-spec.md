---
trigger: linear.issue.created
phase: backlog-research-branch
project: NovelGuard
team: NovelGuard
repo: F:/Python_Projects/NovelGuard
commit: false
base_branch: main
---

@docs/agents/runner-brief.md

# Backlog → research → branch

**Issue:** `{{ISSUE_IDENTIFIER}}` · **Entry:** Backlog · **Exit:** Todo + `auto:research-done`

Research (read-only) → Linear comment → feature branch for later impl. **No PR, no product edits.**

## Gate — fail = STOP

| Check | Action |
| ----- | ------ |
| project/team ≠ NovelGuard | out of scope / silent exit |
| status ≠ Backlog | silent exit |
| `## Research report` exists, no `regenerate` | idempotent exit |

**Never:** product code, commit (empty branch OK), writing-plans / grill / status-router.

**Labels:** `triaging` → `researching` → `branch-creating` → `research-done`

## Do

1. **Load** — `get_issue` + `list_comments`. Parse Problem, AC, `files_allowed`. → In Progress, `auto:triaging`.
2. **Research** — read-only `/caveman`; scoped `src/` / `web/` / `tests/`. → `auto:researching`.  
   Blocked → `## Research blocked`, `auto:blocked`, Backlog, STOP.
3. **Comment** — `## Research report — {{ISSUE_IDENTIFIER}}`: **Summary (caveman)**, Problem, Root cause, Fix locations, AC, Verify commands, Risks.
4. **Branch** — `ai/{{ISSUE_IDENTIFIER}}-<slug>`: fetch, pull base, checkout -b, push -u. Append `## Branch ready` (name, base, reuse in 02/03). → `auto:branch-creating`.
5. **Closeout** — Todo, `auto:research-done`. STOP.

**Tools:** Linear MCP · git (branch + push only)
