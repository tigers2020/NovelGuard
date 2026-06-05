---
trigger: linear.statusChanged
project: NovelGuard
team: private
repo: F:/Python_Projects/NovelGuard
commit: false
---

@docs/agents/runner-brief.md

# Status router — Todo → In Progress

**Issue:** `{{ISSUE_IDENTIFIER}}` · **URL:** `{{ISSUE_URL}}` · **Job:** `{{JOB_ID}}`  
**Task:** {{TASK}}

**HARD-GATE:** Linear MCP on **exactly** `{{ISSUE_IDENTIFIER}}` only.

**One run = one phase.** Exit after status/label update. **No In Review** in this pipeline.

## Gate

| Check | Action |
| ----- | ------ |
| project ≠ NovelGuard | silent exit |
| status ∉ {Todo, Backlog} | silent exit |
| idempotent (done label + no `regenerate *`) | silent exit |

**Never:** `src/`/`web/`/`tests/` edits, commit, branch, PR.

**States (PRI, match by name):** Backlog · Todo · In Progress (final for Phase 3)

**Closeout rule:** every phase exit MUST use **one** `save_issue` with **both** target status and done label. Label-only updates are unreliable for chaining.

## Skip / advance (before phase body)

| status | label | action |
| ------ | ----- | ------ |
| Todo | `auto:research-done` | Spec+brainstorm exist → Skip P1 → `save_issue(Backlog, labels+=auto:spec-done)` MUST |
| Todo | `auto:plan-done` | Spec+Plan exist → run **Phase 3** |
| Todo | `auto:grill-needs-revision` | run **Phase 2R** |
| Backlog | `auto:spec-done` | Plan+grill APPROVED → Skip P2 → `save_issue(Todo, labels+=auto:plan-done)` MUST |

`regenerate spec` disables skip for Phase 1.

## Defer (wrong state for Phase 2)

| status | labels | action |
| ------ | ------ | ------ |
| Todo | `auto:spec-done`, NOT `auto:plan-done` | `save_issue(state=Backlog)` **only** — MUST. STOP. (Re-triggers Phase 2 at Backlog.) |

## Route

```
Todo + auto:research-done     → Phase 1 Spec        → save_issue(Backlog, auto:spec-done) MUST
Backlog + auto:spec-done      → Phase 2 Grill+Plan  → save_issue(Todo, auto:plan-done | auto:grill-needs-revision) MUST
Todo + auto:grill-needs-revision → Phase 2R Spec revise → save_issue(Backlog, auto:spec-done) MUST
Todo + auto:plan-done         → Phase 3 Todo list     → save_issue(In Progress, auto:todo-list-done) MUST → triggers 02
```

### Phase 1 — Spec (Todo → Backlog)

/brainstorming · read-only. Need `## Research report`. Post `## Brainstorm triage report` (**Summary caveman** + triage) + `## Spec` (**Summary caveman** at top). Labels: `auto:spec-brainstorming` → `auto:spec-done`. **Closeout MUST:** `save_issue(state=Backlog, labels+=auto:spec-done)`.

### Phase 2 — Grill + Plan (Backlog → Todo)

**Entry status MUST be Backlog.** /grill-me · /writing-plans · read-only. `## Grill-me verdict` (**Summary caveman**). NEEDS_REVISION → `save_issue(Todo, auto:grill-needs-revision)` MUST. APPROVED → `## Implementation Plan` (**Summary caveman** at top) → `save_issue(Todo, auto:plan-done)` MUST.

### Phase 2R — Spec revision

Fix grill blockers → `## Spec (revised)` → `save_issue(Backlog, auto:spec-done)` MUST.

### Phase 3 — Todo list (Todo → In Progress)

Need Spec + Plan. Post `## Todo list` → `save_issue(In Progress, auto:todo-list-done)` MUST → triggers `02-linear-in-progress-implement.md`.

**Tools:** Linear MCP · read-only repo
