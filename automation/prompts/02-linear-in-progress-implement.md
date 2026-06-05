---
trigger: linear.statusChanged
phase: in-progress-implement
project: NovelGuard
team: NovelGuard
repo: F:/Python_Projects/NovelGuard
commit: true
safety_level: 3
base_branch: main
---

@docs/agents/runner-brief.md

# In Progress → implement → In Review

**Issue:** `{{ISSUE_IDENTIFIER}}` · **URL:** `{{ISSUE_URL}}` · **Job:** `{{JOB_ID}}`  
**HARD-GATE:** Linear MCP on **exactly** `{{ISSUE_IDENTIFIER}}` only.

**Entry:** In Progress + valid Plan/Todo · **Exit:** In Review + `auto:impl-done`

## Gate

| Check | Action |
| ----- | ------ |
| project/team ≠ NovelGuard | silent exit |
| status ≠ In Progress | silent exit |
| `auto:impl-done` + no `regenerate impl` | idempotent exit |
| missing Plan or Todo list | `## Implementation blocked`, `auto:impl-blocked` |

Entry: `status=In Progress` AND (`auto:todo-list-done` OR valid Plan+Todo without impl-done/blocked).

**Never:** merge main, new test files, destructive moves, rewrite Spec/Plan/Todo comments.

**Labels:** `implementing` → `impl-running` → `impl-verifying` → `impl-done`

## Do

1. **Load** — issue, comments, labels. Map open Todo → Plan tasks. `auto:implementing`.
2. **Implement** — inside-out per `docs/current_architecture.md`; respect `files_allowed`; smallest diff. `auto:impl-running`.  
   Blocked → `## Implementation blocked`, `auto:impl-blocked`, STOP.
3. **Verify** — scoped pytest; web lint if touched. `auto:impl-verifying`. One fix retry max.
4. **Commit** — branch from `## Branch ready` or `ai/{{ISSUE_IDENTIFIER}}-impl`; push; optional `gh pr create` (no merge).
5. **Report** — `## Implementation report`: **Summary (caveman)**, Todo done table, changed files, verification (cmd + exit), PR link, risks. → In Review, `auto:impl-done`. STOP.

/executing-plans · /subagent-driven-development

**Tools:** Linear MCP · git · `gh pr create`
