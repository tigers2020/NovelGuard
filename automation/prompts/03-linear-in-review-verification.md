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

@docs/agents/runner-brief.md

# In Review → tests → PR → babysit → Done

**Issue:** `{{ISSUE_IDENTIFIER}}` · **URL:** `{{ISSUE_URL}}` · **Job:** `{{JOB_ID}}`  
**HARD-GATE:** Linear MCP on **exactly** `{{ISSUE_IDENTIFIER}}` only.

**Entry:** In Review · **Exit:** Done + `auto:verify-done` OR In Progress rebuke + `auto:verify-failed`

**TEST_ALLOWED** — new/extended tests per Spec + Plan + Todo.

## Gate

| Check | Action |
| ----- | ------ |
| project/team ≠ NovelGuard | silent exit |
| status ≠ In Review | silent exit |
| `auto:verify-done` + no `regenerate verify` | idempotent exit |
| missing Spec/Plan/Todo | `## Verification blocked`, `auto:verify-blocked` |

**Labels:** `verifying` → `verify-testing` → `verify-fixing` → `verify-pr` → `verify-babysit` → `verify-done` | `verify-failed`

## Do

1. **Load** — Spec, Plan, Todo, Implementation report. Build AC → test matrix. `auto:verifying` → `auto:verify-testing`.
2. **Write tests** — extend or add per matrix (TEST_ALLOWED). Commit on impl branch.
3. **Green loop** — pytest, contracts, lint, `verify_phase_completion.py`. Max 5 cycles. `auto:verify-fixing`.
4. **PR** — /finishing-a-development-branch: push + `gh pr create` (no merge). `auto:verify-pr`.
5. **Babysit** — /babysit until merge-ready. `auto:verify-babysit`.
6. **Done** — `## Verification report`: **Summary (caveman)**, test matrix↔AC, tests changed, commands (pass), PR URL, babysit status → Done + `auto:verify-done`.  
   **Rebuke** — `## Verification rebuke`: **Summary (caveman)**, failures, required fixes, PR URL → In Progress + `auto:verify-failed`. STOP.

**Tools:** Linear MCP · git · `gh` · pytest · npm
