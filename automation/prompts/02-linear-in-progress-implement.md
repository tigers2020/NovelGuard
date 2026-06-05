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

@AGENTS.md @.cursor/rules/00-automation-core.mdc @.cursor/rules/10-runner-safety.mdc

# In Progress → DDD implement → In Review

**Issue:** `{{ISSUE_IDENTIFIER}}` · **URL:** `{{ISSUE_URL}}` · **Job:** `{{JOB_ID}}`  
**HARD-GATE:** Linear MCP on **exactly** `{{ISSUE_IDENTIFIER}}` only.

**Trigger:** `linear.statusChanged` · **Team / project:** **NovelGuard**  
**Entry:** In Progress + valid label/comments · **Exit:** **In Review** + `auto:impl-done` → **STOP**

## Gate — invalid = STOP

| Check | Valid → proceed |
| ----- | ---------------- |
| project ≠ NovelGuard | silent exit |
| team ≠ NovelGuard | silent exit |
| status ≠ In Progress | silent exit |
| `currentAutoLabel == auto:impl-done` + no `regenerate impl` | idempotent exit |
| missing `## Implementation Plan` or `## Todo list` | `## Implementation blocked`, `auto:impl-blocked` |

**Entry valid when:**

```text
status.name == "In Progress"
AND (
  currentAutoLabel == auto:todo-list-done
  OR (Plan + Todo list comments exist AND label ∉ {auto:impl-done, auto:impl-blocked})
)
```

Resolve states via `list_issue_statuses` (team **NovelGuard**). Match by **name** if ids drift.

**Never:** merge main, new test files, destructive moves without dry-run note, rewrite Spec/Plan/Todo comments.

**Labels:** one `auto:*`; keep non-`auto:` labels.

`implementing` → `impl-running` → `impl-verifying` → `impl-done`

---

## DDD — coding rules

Layers (`docs/current_architecture.md`): **domain** → **application** → **infrastructure** → **web** → **app**.

| Layer | Rule |
| ----- | ---- |
| **domain** | Pure logic, no I/O, no framework imports |
| **application** | Use cases, orchestration; calls domain + ports |
| **infrastructure** | Adapters, filesystem, DB, external APIs |
| **web** | UI only; no business rules |
| **app** | Bridge/wiring |

Implement Plan tasks **inside-out**: domain first → application → infra → web.  
Respect `files_allowed` in `## Spec`. Smallest diff. No unrelated refactors.

/executing-plans · /subagent-driven-development

---

## Do (in order)

### 1. Load

`get_issue` + `list_comments` + collect label.  
Load `## Spec`, `## Implementation Plan`, `## Todo list`.  
Map open Todo `- [ ]` → Plan tasks.  
`auto:implementing`.

### 2. Implement (Todo order)

`auto:impl-running`.

Per task: DDD layer order · repo conventions · no new test files.  
Blocked → `## Implementation blocked`, `auto:impl-blocked`, stay In Progress, **STOP**.

### 3. Verify

`auto:impl-verifying`.

```bash
pytest <scoped> -v
cd web && npm run lint          # if web touched
python scripts/verify_phase_completion.py   # when appropriate
```

Fail after one fix retry → blocked, **STOP**.

### 4. Commit (+ optional PR)

Branch: reuse from 00 `## Branch ready` / Research report; else `ai/{{ISSUE_IDENTIFIER}}-impl`.
Commit (why + issue id) → push → optional `gh pr create` (no merge).

### 5. Report + closeout

`save_comment` **`## Implementation report`**: Summary (caveman), Todo done table, changed files, verification, PR link, risks.

`save_issue`: **In Review**, `auto:impl-done`. **STOP**.

---

## End-to-end

```text
01 router Phase 3 → In Progress + auto:todo-list-done
       ↓ statusChanged
[THIS] gate OK → DDD implement → verify → commit → In Review + auto:impl-done
       ↓ statusChanged
03 verification → tests + loop → Done | In Progress (rebuke)
```

---

## Tools

Linear MCP (team **NovelGuard**) · git · `gh pr create` · scoped repo writes
