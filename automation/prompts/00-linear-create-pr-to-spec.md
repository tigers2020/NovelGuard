---
trigger: linear.issue.created
phase: backlog-research-branch
project: NovelGuard
team: NovelGuard
repo: F:/Python_Projects/NovelGuard
commit: false
base_branch: main
---

@AGENTS.md @.cursor/rules/00-automation-core.mdc @.cursor/rules/10-runner-safety.mdc

# Backlog → research → branch → Todo

**Issue:** `{{ISSUE_IDENTIFIER}}` · **Trigger:** `linear.issue.created` · **Entry:** Backlog · **Exit:** Todo + `auto:research-done`

Research (read-only) → Linear comment → **feature branch 생성** (impl/verify에서 사용). **PR 없음.**

## Gate — fail = STOP

| Check | Action |
| ----- | ------ |
| project ≠ NovelGuard | comment `## Out of scope` |
| team ≠ NovelGuard | silent exit |
| status ≠ Backlog | silent exit |
| `## Research report` exists, no `regenerate` | idempotent exit |
| blocked | `auto:blocked`, Backlog |

**Never:** product code edits, commit (empty branch OK), PR, writing-plans / grill / status-router.

**Branch only:** `git fetch` · checkout `main` · `git pull` · `git checkout -b` · `git push -u origin` — no impl commits in this run.

**States (team NovelGuard, match by name):** Backlog (entry) · In Progress (work) · Todo (final)

**Labels:** `triaging` → `researching` → `branch-creating` → `research-done`

---

## Do (in order)

### 1. Load

`get_issue` + `list_comments`. Parse Problem, AC, `files_allowed`.  
`save_issue`: **In Progress**, `auto:triaging`.

### 2. Research (read-only)

/caveman · `AGENTS.md` + scoped read `src/` / `web/` / `tests/`.

`auto:researching`.

Deliver: problem, root cause + paths, fix locations, verify commands, risks.

Blocked → `## Research blocked`, `auto:blocked`, Backlog, STOP.

### 3. Comment

`save_comment` **`## Research report — {{ISSUE_IDENTIFIER}}`**: Summary (caveman), Problem, Root cause, Fix locations, AC, Verification commands, Risks.

### 4. Create branch (for later impl / verify)

`auto:branch-creating`

```text
ai/{{ISSUE_IDENTIFIER}}-<slug-from-title>
```

1. `git fetch origin`
2. checkout + pull `main` (or issue-stated base)
3. `git checkout -b ai/{{ISSUE_IDENTIFIER}}-<slug>`
4. `git push -u origin HEAD` — same tip as base, no new commits required

Append to report comment (or `save_comment` **`## Branch ready`**):

```markdown
### Branch

- name: `ai/{{ISSUE_IDENTIFIER}}-<slug>`
- base: main
- use: 02 implement · 03 verify (reuse this branch)
```

If push fails → `## Research blocked` + branch error, `auto:blocked`, STOP.

### 5. Closeout

`save_issue`: **Todo**, `auto:research-done`. **STOP**.

---

## End-to-end

```text
Issue created (Backlog)
       ↓
research comment → branch push → Todo + auto:research-done
       ↓
01 status router (planning pipeline)
       ↓
02 / 03 reuse branch ai/{{ISSUE_IDENTIFIER}}-*
```

---

## Tools

Linear MCP · git (branch + push only, no product writes)
