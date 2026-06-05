---
trigger: linear.statusChanged
phase: in-review-verification
project: NovelGuard
team: NovelGuard
repo: F:/Python_Projects/NovelGuard
commit: true
safety_level: 3
base_branch: main
---

@AGENTS.md @.cursor/rules/00-automation-core.mdc @.cursor/rules/10-runner-safety.mdc

# In Review → tests → PR → babysit → Done | In Progress

**Issue:** `{{ISSUE_IDENTIFIER}}` · **URL:** `{{ISSUE_URL}}` · **Job:** `{{JOB_ID}}`  
**HARD-GATE:** Linear MCP on **exactly** `{{ISSUE_IDENTIFIER}}` only.

**Trigger:** `linear.statusChanged` · **Team / project:** **NovelGuard**  
**Entry:** In Review + valid · **Exit:** **Done** (merge-ready) or **In Progress** (rebuke) → **STOP**

**TEST_ALLOWED** — new/extended test files from Spec + Plan + Todo.

## Gate — invalid = STOP

| Check | Action |
| ----- | ------ |
| project ≠ NovelGuard | silent exit |
| team ≠ NovelGuard | silent exit |
| status ≠ In Review | silent exit |
| `auto:verify-done` + no `regenerate verify` | idempotent exit |
| missing Spec / Plan / Todo list | `## Verification blocked`, `auto:verify-blocked`, STOP |

**Entry valid:**

```text
status == "In Review"
AND (currentAutoLabel == auto:impl-done OR Spec+Plan+Todo valid)
```

States (team **NovelGuard**, match by name): **In Review** · **In Progress** · **Done**.

**Never:** merge to main without approval, destructive moves without dry-run note.

**Labels:** `verifying` → `verify-testing` → `verify-fixing` → `verify-pr` → `verify-babysit` → `verify-done` | `verify-failed`

---

## Do (in order)

### 1. Load + test matrix

`get_issue` + `list_comments` + label.

Load `## Spec`, `## Implementation Plan`, `## Todo list`, `## Implementation report`.

Matrix: every AC + Plan verify + Todo verification item → ≥1 test.

`auto:verifying` → `auto:verify-testing`

### 2. Write tests (new files OK)

Spec + Plan + Todo 종합 → pytest / contract / e2e.

- Prefer extend existing `tests/`; **new file when AC requires** (this prompt = TEST_ALLOWED)
- Domain: pure · Web: contracts/e2e when UI AC
- Commit on branch from **00** (`## Branch ready`) or `ai/{{ISSUE_IDENTIFIER}}-impl`

### 3. Run → fix loop (until green)

`auto:verify-fixing`

```bash
pytest <scoped> -v
cd web && npm run test:contracts
cd web && npm run lint
python scripts/verify_phase_completion.py
```

Loop until **all green** or **max 5** cycles.

**Still red** → §6 rebuke (skip PR/babysit).

### 4. /finishing-a-development-branch → PR

Tests green only.

/finishing-a-development-branch

Automation path = **Option 2: Push + PR** (no local merge, no discard):

1. Re-run test matrix — must pass (skill Step 1)
2. Base branch: `main`
3. `git push -u origin HEAD`
4. `gh pr create` — Summary, Test plan (from matrix), Linear issue link
5. Record PR URL

`auto:verify-pr`

**No merge to main** without human approval.

### 5. /babysit

/babysit

Until PR **merge-ready** (or blocker):

- Resolve merge conflicts (preserve branch intent)
- Triage unresolved review comments + Bugbot (valid only)
- Fix CI in PR scope; re-push; re-watch until green + mergeable
- Do **not** weaken CI workflows to pass

`auto:verify-babysit`

If babysit exhausts scope → §6 rebuke with PR URL + CI/comment blockers.

### 6a. Merge-ready → Done

`save_comment` **`## Verification report`**: Summary (/caveman), test matrix↔AC, tests added/changed, commands (pass), PR URL, babysit status.

`save_issue`: **Done**, `auto:verify-done`. **STOP**

### 6b. Rebuke → In Progress

`save_comment` **`## Verification rebuke`**: failures (tests / CI / review), required fixes, PR URL if exists.

`save_issue`: **In Progress**, `auto:verify-failed`. **STOP**

---

## End-to-end

```text
02 → In Review + auto:impl-done
       ↓
03: write tests → green loop
       ↓
finishing-a-development-branch → push + PR
       ↓
babysit → merge-ready
       ├ OK → Done + auto:verify-done
       └ fail → rebuke → In Progress + auto:verify-failed
```

---

## Tools

Linear MCP · git · `gh pr create` / `gh pr checks` · pytest · npm
