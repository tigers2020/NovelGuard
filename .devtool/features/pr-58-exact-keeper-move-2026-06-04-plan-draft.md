---
id: pr-58-exact-keeper-move-2026-06-04-plan-draft
status: plan-review
work_id: pr-58-exact-keeper-move-2026-06-04
automation_state: approved
linked_inbox: .devtool/features/done/pr-58-exact-keeper-move-2026-06-04-inbox.md
linked_spec: .devtool/features/pr-58-exact-keeper-move-2026-06-04-spec-draft.md
files_allowed: null
branch: feat/pr-58-exact-keeper-move-2026-06-04
approved: true
approved_by: rehydrate_planning_cards
approved_at: auto
---

# [Plan Draft] pr-58-exact-keeper-move-2026-06-04

## Spec link

- .devtool/features/pr-58-exact-keeper-move-2026-06-04-spec-draft.md

## Architecture

Trace exact duplicate flow from Resolve approve through review state merge into preview/apply. Fix keeper vs move_duplicate derivation in merge/reconcile, ensure build_preview_plan emits move_duplicate ops for approved non-keepers, then align UI row display after reload.

## Implementation tasks

- Reproduce bug: scan library with byte-identical files, approve exact group in Resolve, run preview and apply; document keeper vs move_duplicate row state before/after reload
- Fix review_state_merge + reconcile_approved_duplicate_proposed_actions so approved exact groups assign keep to one keeper and move_duplicate to others (`src/application/review_state_merge.py`, `src/application/review_move_targets.py`)
- Fix build_preview_plan / move selection to include approved non-keeper exact rows as move_duplicate into duplicate/ (`src/app/build_preview_plan.py`, `src/application/review_move_targets.py`)
- Fix Resolve UI + bridge contract so proposedAction and keeperLabel persist correctly after reload (`web/src/`, tests/contracts as needed)
- Add regression test: approve exact group → preview → apply; assert keeper on disk, non-keepers under duplicate/ (`tests/` bridge or kiwi e2e)

## Files allowed

- src/
- web/src/
- tests/
- scripts/
- .devtool/features/

## Verification matrix

| Criterion | Command |
|---|---|
| Review merge / reconcile | `pytest tests/ -k "duplicate or review_state or reconcile" -v` |
| Preview plan move ops | `pytest tests/ -k "preview_plan or build_preview" -v` |
| End-to-end exact keeper move | `pytest tests/ -k "exact" -v` or `cd web && npm run test:e2e` (exact duplicate flow) |
| Repo phase gate | `python scripts/verify_phase_completion.py` |

## Risks

- Near/relation duplicate rows regress if shared helpers change without exact-only guards.
- Apply could move keeper if keeper_id resolution is wrong.

## Rollback plan

- Revert changed files on branch `feat/pr-58-exact-keeper-move-2026-06-04` after human review.

## Branch name

- `feat/pr-58-exact-keeper-move-2026-06-04`
