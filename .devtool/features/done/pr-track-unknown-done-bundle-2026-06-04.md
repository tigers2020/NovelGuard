---
id: pr-track-unknown-done-bundle-2026-06-04
status: done
priority: low
assignee: null
epic: null
dueDate: null
created: "2026-06-04T15:30:35.000Z"
modified: "2026-06-04T15:52:28Z"
completedAt: null
labels:
  - bundle
  - roadmap-pr
  - track-unknown
bundle: true
bundle_kind: "pr:unknown"
order: z0
---

# Track unknown — PR done bundle

| Field | Value |
|-------|-------|
| **Track** | unknown |
| **Members** | 5 card(s) |


## Bundled cards

### Exact duplicates: keep one keeper, move others on apply

| Field | Value |
|-------|-------|
| **Track** | resolve |

## Scope

User report: exact (type exact) duplicate files should leave one copy in the library and move the rest to duplicate/, but the app is not doing so end-to-end. Investigate approve, review state merge, preview selection, and apply paths (review_rows_builder, review_state_merge, reconcile_approved_duplicate_proposed_actions, build_preview_plan). Reproduce: scan with byte-identical files, approve exact group in Resolve, preview, apply. Near/relation policy unchanged unless required for exact parity.

## Acceptance

After approving an exact duplicate group (>=2 members), preview/apply moves every non-keeper to duplicate/ while the keeper path stays on disk; Resolve rows show keep vs move_duplicate consistently after reload; regression test (bridge or kiwi e2e) covers approve -> preview -> apply.

## files_allowed

- `src/`
- `web/src/`
- `tests/`
- `scripts/`
- `.devtool/features/`

### [Spec Draft] pr-58-exact-keeper-move-2026-06-04

## Problem

# Exact duplicates: keep one keeper, move others on apply

| Field | Value |
|-------|-------|
| **Track** | resolve |

## Scope

User report: exact (type exact) duplicate files should leave one copy in the library and move the rest to duplicate/, but the app is not doing so end-to-end. Investigate approve, review state merge, preview selection, and apply paths (review_rows_builder, review_state_merge, reconcile_approved_duplicate_proposed_actions, build_preview_plan). Reproduce: scan with byte-identical files, approve exact group in Resolve, preview, apply. Near/relation policy unchanged unless required for exact parity.

## Acceptance

After approving an exact duplicate group (>=2 members), preview/apply moves every non-keeper to duplicate/ while the keeper path stays on disk; Resolve rows show keep vs move_duplicate consistently after reload; regression test (bridge or kiwi e2e) covers approve -> preview -> apply.

## files_allowed

- `src/`
- `web/src/`
- `tests/`
- `scripts/`
- `.devtool/features/`

## Goals

- Preserve the requested behavior.
- Keep changes inside the declared files_allowed boundary.

## Non-goals

- No product-code implementation during planning automation.
- No deletion of Inbox, Spec, Plan, or Todo audit cards.

## Decisions

- Use local-only Kanban automation.
- Keep Ready/Ready Gate behavior as gate-check only.

## UX impact

- To be confirmed against acceptance before implementation.

## Backend impact

- To be confirmed against acceptance before implementation.

## Safety impact

- Product code is blocked until the Scheduled card moves to In Progress.

## Acceptance criteria

After approving an exact duplicate group (>=2 members), preview/apply moves every non-keeper to duplicate/ while the keeper path stays on disk; Resolve rows show keep vs move_duplicate consistently after reload; regression test (bridge or kiwi e2e) covers approve -> preview -> apply.

## files_allowed proposal

- .devtool/features/
- scripts/
- src/
- web/src/

## Internal Grill Review

_automation_at: 2026-06-04T15:30:54Z_

- No blocking gaps found.

## Internal Grill Review

_automation_at: 2026-06-04T15:43:56Z_

- No blocking gaps found.

### [Plan Draft] pr-58-exact-keeper-move-2026-06-04-spec-draft

## Spec link

- .devtool/features/pr-58-exact-keeper-move-2026-06-04-spec-draft.md

## Implementation tasks

- Implement the approved acceptance criteria inside files_allowed only.
- Record changed paths and verification commands.

## Files allowed

- .devtool/features/
- scripts/
- src/
- web/src/

## Verification matrix

- `python scripts/verify_phase_completion.py` if present.
- Targeted tests listed by the implementation card or plan.

## Risks

- Scope creep outside files_allowed.
- Missing evidence for verification.

## Rollback plan

- Revert only changed files for this work item after human review.

## Branch name

- `feat/pr-58-exact-keeper-move-2026-06-04-spec-draft`

## Plan Gap Table

_automation_at: 2026-06-04T15:44:14Z_

| Spec requirement | Plan coverage | Status | Fix |
|---|---|---|---|
| Acceptance criteria | Verification matrix | pass | none |

### [Scheduled] pr-58-exact-keeper-move-2026-06-04-spec-draft

## Links

- Inbox: .devtool/features/pr-58-exact-keeper-move-2026-06-04-spec-draft.md
- Spec: .devtool/features/pr-58-exact-keeper-move-2026-06-04-spec-draft.md
- Plan: .devtool/features/pr-58-exact-keeper-move-2026-06-04-spec-draft-plan-draft.md
- Todo: .devtool/features/pr-58-exact-keeper-move-2026-06-04-spec-draft-todo.md

## Acceptance

See linked Inbox and Spec.

## files_allowed

- .devtool/features/
- scripts/
- src/
- web/src/

## Branch

- `feat/pr-58-exact-keeper-move-2026-06-04-spec-draft`

## Automation Gate Feedback

_automation_at: 2026-06-04T15:44:14Z_

- BLOCKED: linked spec missing

## Automation Gate Feedback

_automation_at: 2026-06-04T15:44:16Z_

- BLOCKED: linked spec missing

## Automation Gate Feedback

_automation_at: 2026-06-04T15:44:18Z_

- BLOCKED: linked spec missing

## Automation Gate Feedback

_automation_at: 2026-06-04T15:44:20Z_

- BLOCKED: linked spec missing

## Automation Gate Feedback

_automation_at: 2026-06-04T15:44:22Z_

- BLOCKED: linked spec missing

## Automation Gate Feedback

_automation_at: 2026-06-04T15:44:24Z_

- BLOCKED: linked spec missing

## Automation Gate Feedback

_automation_at: 2026-06-04T15:44:26Z_

- BLOCKED: linked spec missing

## Automation Gate Feedback

_automation_at: 2026-06-04T15:44:28Z_

- BLOCKED: linked spec missing

## Automation Gate Feedback

_automation_at: 2026-06-04T15:44:30Z_

- BLOCKED: linked spec missing

## Automation Gate Feedback

_automation_at: 2026-06-04T15:44:32Z_

- BLOCKED: linked spec missing

## Automation Gate Feedback

_automation_at: 2026-06-04T15:44:34Z_

- BLOCKED: linked spec missing

## Automation Gate Feedback

_automation_at: 2026-06-04T15:44:36Z_

- BLOCKED: linked spec missing

## Automation Gate Feedback

_automation_at: 2026-06-04T15:44:38Z_

- BLOCKED: linked spec missing

## Automation Gate Feedback

_automation_at: 2026-06-04T15:44:40Z_

- BLOCKED: linked spec missing

## Automation Gate Feedback

_automation_at: 2026-06-04T15:44:42Z_

- BLOCKED: linked spec missing

### [Todo] pr-58-exact-keeper-move-2026-06-04-spec-draft

## Checklist

- [ ] T1
  - files_allowed: .devtool/features/, scripts/, src/, web/src/
  - expected verification: `python scripts/verify_phase_completion.py` if present
  - risk: scope creep outside files_allowed
