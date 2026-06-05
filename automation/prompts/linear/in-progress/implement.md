---
trigger: linear.status→In Progress
phase: implement
project: NovelGuard
team: NovelGuard
repo: F:/Python_Projects/NovelGuard
commit: true
safety_level: 3
base_branch: main
---

@docs/agents/runner-brief-compact.md

## Context memory
{{CONTEXT_MEMORY_JSON}}

# In Progress → implement → In Review

**Issue:** `{{ISSUE_IDENTIFIER}}` · **URL:** `{{ISSUE_URL}}` · **Job:** `{{JOB_ID}}`  
**HARD-GATE:** Linear MCP on **exactly** `{{ISSUE_IDENTIFIER}}` only.

**Entry:** In Progress + Plan/Task list · **Exit:** In Review + `auto:impl-done`

## Gate

| Check | Action |
| ----- | ------ |
| project/team ≠ NovelGuard | silent exit |
| status ≠ In Progress | silent exit |
| `auto:impl-done` + no `regenerate impl` | idempotent exit |
| missing Plan or Task list | `## Implementation blocked`, `auto:impl-blocked` |

Entry: `auto:todo-list-done` (task-list-done) OR valid Plan+Task list without impl-done/blocked.

**Never:** merge main, new test files, destructive moves, rewrite Spec/Plan/Task list comments.

Progress labels (`implementing`, `impl-running`, `impl-verifying`) — **no separate `save_issue`**.

## Do

1. **Load** — issue, comments, labels. Map open **Task list** checkboxes → plan tasks.
2. **Implement — REQUIRED:** `/subagent-driven-development` only (fresh subagent per plan task; spec review then code-quality review; no `/executing-plans`). Inside-out per `docs/current_architecture.md`; respect `files_allowed`; smallest diff.  
   Blocked → `## Implementation blocked`, `auto:impl-blocked`, STOP.
3. **Verify** — scoped pytest; web lint if touched. One fix retry max.
4. **Commit** — branch from `## Branch ready` or `ai/{{ISSUE_IDENTIFIER}}-impl`; push; optional `gh pr create` (no merge).
5. **Report** — `## Implementation report`: **Summary (caveman)**, Task list done table, changed files, verification (cmd + exit), PR link, risks.

**Closeout — MUST** — `save_issue(state=In Review, labels+=auto:impl-done)` **one call**. STOP. → `linear/in-review/verify.md`.

/subagent-driven-development

**Tools:** Linear MCP · git · `gh pr create`
