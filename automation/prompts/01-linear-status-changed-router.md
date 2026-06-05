---
trigger: linear.statusChanged
project: NovelGuard
team: private
repo: F:/Python_Projects/NovelGuard
commit: false
---

@AGENTS.md @.cursor/rules/00-automation-core.mdc @.cursor/rules/10-runner-safety.mdc

# Status router — Todo entry → In Progress exit

**Issue:** `{{ISSUE_IDENTIFIER}}` · **URL:** `{{ISSUE_URL}}` · **Job:** `{{JOB_ID}}`  
**Task:** {{TASK}}

**HARD-GATE:** Linear MCP `get_issue` + `list_comments` on **exactly** `{{ISSUE_IDENTIFIER}}` only. Do not substitute another issue.

**Trigger:** `linear.statusChanged` · **Entry:** **Todo** (`00-linear-create-pr-to-spec.md` — research + branch)  
**Exit:** **In Progress** + `auto:todo-list-done` → **STOP**

**In Review = verification 전용** (impl 완료 후). planning pipeline에서 **In Review 사용 금지**.

한 run = **한 phase만**. status 변경 → 다음 automation run. 같은 run에서 다음 phase **금지**.

## Gate — fail = STOP

| Check | Action |
| ----- | ------ |
| project ≠ NovelGuard | silent exit |
| status ∉ {Todo, Backlog} | silent exit |
| idempotent (label done + no `regenerate *`) | silent exit |

**Never:** `src/`/`web/`/`tests/` edits, commit, branch, PR, **In Review** status set.

**States (private / PRI):** Backlog `441d268f…` · Todo `8dac25f9…` · In Progress `362e9f77…` (final)

**Labels:** one `auto:*`; keep non-`auto:` labels.

Collect each run: `currentAutoLabel`, latest comment headers (`## Spec`, `## Brainstorm triage report`, etc.).

---

## Skip / advance (label + comment)

**Run before phase work.** 한 run = still one action (skip-advance **or** one phase body — not both).

Issue body `regenerate spec` → skip rules **off** for Phase 1; run Phase 1.

| status | label | comments | action |
| ------ | ----- | -------- | ------ |
| Todo | `auto:research-done` | Spec + brainstorm **both** exist | **Skip Phase 1** → `save_issue` Backlog + `auto:spec-done` → STOP |
| Todo | `auto:spec-done` | Spec + brainstorm exist | **Skip Phase 1** (status lag) → `save_issue` Backlog + `auto:spec-done` → STOP |
| Todo | `auto:plan-done` | Spec + Plan exist | **Skip Phase 1–2** → run **Phase 3** |
| Todo | `auto:grill-needs-revision` | verdict NEEDS_REVISION | **Skip Phase 1** → run **Phase 2R** |
| Backlog | `auto:spec-done` | Spec + Plan + grill APPROVED | **Skip Phase 2** → `save_issue` Todo + `auto:plan-done` → STOP |
| Backlog | `auto:spec-done` | Spec only, no Plan | run **Phase 2** (normal) |
| any | `auto:todo-list-done` | Todo list exists | idempotent STOP |
| any | `auto:plan-done` | Plan exists, no Todo list | route **Phase 3** (if status Todo) |

**Phase 1 in-flight resume:** label `auto:spec-brainstorming` on Todo → run Phase 1 from step 2 (don't restart if brainstorm+Spec already posted).

**Skip never:** impl labels (`auto:todo-list-done`+), `regenerate *` without matching work, missing required comments for target phase.

---

## Route (status + label)

**Order:** Skip/advance table first → else:

```
Todo + auto:research-done           → Phase 1 (Spec)          → Backlog
Backlog + auto:spec-done            → Phase 2 (Grill+Plan)    → Todo
Todo + auto:grill-needs-revision    → Phase 2R (Spec revise)  → Backlog
Todo + auto:plan-done               → Phase 3 (Todo list)     → In Progress ★
else                                → STOP
```

| Phase | Entry | Label | Work | Exit | Label |
| ----- | ----- | ----- | ---- | ---- | ----- |
| 1 | Todo | `auto:research-done` | Spec + brainstorm | Backlog | `auto:spec-done` |
| 2 | Backlog | `auto:spec-done` | grill → plan or reject | Todo / Todo | `auto:plan-done` / `auto:grill-needs-revision` |
| 2R | Todo | `auto:grill-needs-revision` | Spec revision | Backlog | `auto:spec-done` |
| 3 | Todo | `auto:plan-done` | todo list | In Progress | `auto:todo-list-done` |

Idempotent STOP:

| status | label | unless |
| ------ | ----- | ------ |
| Backlog | `auto:spec-done` | `regenerate spec` |
| Todo | `auto:plan-done` | `regenerate todo` |
| Todo | `auto:grill-needs-revision` | `regenerate spec` (→ Phase 2R re-run) |
| In Progress | `auto:todo-list-done` | `regenerate todo` |

---

## Phase 1 — Spec (Todo → Backlog)

/brainstorming · /caveman · read-only

**Skip gate (label):** Spec + brainstorm comments already exist → **do not** duplicate; use Skip table → Backlog + `auto:spec-done`.

**Gate:** `## Research report` required. `## Spec` exists + no `regenerate spec` → Skip table or STOP.

1. `auto:spec-brainstorming` (skip if resuming in-flight)
2. Read issue + research + scoped codebase
3. `save_comment` **`## Brainstorm triage report`** (skip if exists + still valid)
4. `save_comment` **`## Spec`** (skip if exists + still valid)
5. `save_issue`: **Backlog**, `auto:spec-done`
6. **STOP**

---

## Phase 2 — Grill + Plan (Backlog → Todo)

/grill-me · /writing-plans · /caveman · read-only

**Gate:** `## Spec` + brainstorm report.

1. `auto:grilling`
2. Self-grill → `save_comment` **`## Grill-me verdict`**
3. **NEEDS_REVISION** → `save_issue`: **Todo**, `auto:grill-needs-revision` → **STOP** (Phase 2R trigger)
4. **APPROVED** → `auto:planning`
5. `save_comment` **`## Implementation Plan`**
6. `save_issue`: **Todo**, `auto:plan-done`
7. **STOP**

---

## Phase 2R — Spec revision (Todo → Backlog)

/grill-me · /brainstorming · /caveman · read-only

**Gate:** latest `## Grill-me verdict` = NEEDS_REVISION. `## Spec` required.

1. `auto:spec-revising`
2. Read verdict `_blockers_` + current Spec/brainstorm + scoped codebase
3. Fix every blocker; no open TBD
4. `save_comment` **`## Spec (revised)`** — or new `## Spec` with `_revision:_` note + changed sections
5. Update **`## Brainstorm triage report`** only if verdict requires it
6. `save_issue`: **Backlog**, `auto:spec-done`
7. **STOP** — Phase 2 re-run via Backlog statusChanged

---

## Phase 3 — Todo list (Todo → In Progress) ★

/caveman · read-only

**Gate:** `## Spec` + `## Implementation Plan`. AC ↔ plan cross-check.

1. `auto:todo-checking`
2. Gap → `## Todo list blocked`, `auto:blocked` → STOP
3. `save_comment` **`## Todo list`**
4. `save_issue`: **In Progress**, `auto:todo-list-done`
5. **STOP** → `02-linear-in-progress-implement.md`

---

## End-to-end

```text
00: … → Todo + auto:research-done
       ↓ Todo
[Skip] Spec+brainstorm exist → Backlog + auto:spec-done (no Phase 1 body)
       ↓ else Phase 1 → Backlog + auto:spec-done
       ↓ Backlog
[Skip] Plan + grill APPROVED → Todo + auto:plan-done
       ↓ else Phase 2: APPROVED → Plan → Todo + auto:plan-done
                 NEEDS_REVISION → Todo + auto:grill-needs-revision
                       ↓ Phase 2R → Backlog + auto:spec-done → Phase 2 loop
       ↓ Todo
Phase 3 → In Progress ★ → 02 → In Review → 03 verify → Done
```

---

## Tools

Linear MCP · read-only repo
