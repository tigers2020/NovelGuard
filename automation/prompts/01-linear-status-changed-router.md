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

## Skip / advance (before phase body)

| status | label | action |
| ------ | ----- | ------ |
| Todo | `auto:research-done` | Spec+brainstorm exist → Skip P1 → Backlog + `auto:spec-done` |
| Todo | `auto:plan-done` | Spec+Plan exist → run **Phase 3** |
| Todo | `auto:grill-needs-revision` | run **Phase 2R** |
| Backlog | `auto:spec-done` | Plan+grill APPROVED → Skip P2 → Todo + `auto:plan-done` |

`regenerate spec` disables skip for Phase 1.

## Route

```
Todo + auto:research-done     → Phase 1 Spec        → Backlog + auto:spec-done
Backlog + auto:spec-done      → Phase 2 Grill+Plan  → Todo + auto:plan-done | auto:grill-needs-revision
Todo + auto:grill-needs-revision → Phase 2R Spec revise → Backlog + auto:spec-done
Todo + auto:plan-done         → Phase 3 Todo list     → In Progress + auto:todo-list-done
```

### Phase 1 — Spec (Todo → Backlog)

/brainstorming · read-only. Need `## Research report`. Post `## Brainstorm triage report` (**Summary caveman** + triage) + `## Spec` (**Summary caveman** at top). Labels: `auto:spec-brainstorming` → `auto:spec-done`.

### Phase 2 — Grill + Plan (Backlog → Todo)

/grill-me · /writing-plans · read-only. `## Grill-me verdict` (**Summary caveman**). NEEDS_REVISION → Todo + `auto:grill-needs-revision`. APPROVED → `## Implementation Plan` (**Summary caveman** at top) → Todo + `auto:plan-done`.

### Phase 2R — Spec revision

Fix grill blockers → `## Spec (revised)` → Backlog + `auto:spec-done`.

### Phase 3 — Todo list (Todo → In Progress)

Need Spec + Plan. Post `## Todo list` → In Progress + `auto:todo-list-done` → triggers `02-linear-in-progress-implement.md`.

**Tools:** Linear MCP · read-only repo
