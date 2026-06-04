---
id: pr-58-exact-keeper-move-2026-06-04-todo
status: todo
work_id: pr-58-exact-keeper-move-2026-06-04
automation_state: created
linked_inbox: .devtool/features/pr-58-exact-keeper-move-2026-06-04-inbox.md
linked_spec: .devtool/features/pr-58-exact-keeper-move-2026-06-04-spec-draft.md
linked_plan: .devtool/features/pr-58-exact-keeper-move-2026-06-04-plan-draft.md
files_allowed: null
---

# [Todo] pr-58-exact-keeper-move-2026-06-04

## Checklist

- [ ] T1
  - task: Reproduce bug: scan library with byte-identical files, approve exact group in Resolve, run preview and apply; document keeper vs move_duplicate row state before/after reload
  - files_allowed: .devtool/features/, scripts/, src/, web/src/
  - expected verification: `python scripts/verify_phase_completion.py` if present
  - risk: scope outside files_allowed for this chunk

- [ ] T2
  - task: Fix review_state_merge + reconcile_approved_duplicate_proposed_actions so approved exact groups assign keep to one keeper and move_duplicate to others (`src/application/review_state_merge.py`, `src/application/review_move_targets.py`)
  - files_allowed: .devtool/features/, scripts/, src/, web/src/
  - expected verification: `python scripts/verify_phase_completion.py` if present
  - risk: scope outside files_allowed for this chunk

- [ ] T3
  - task: Fix build_preview_plan / move selection to include approved non-keeper exact rows as move_duplicate into duplicate/ (`src/app/build_preview_plan.py`, `src/application/review_move_targets.py`)
  - files_allowed: .devtool/features/, scripts/, src/, web/src/
  - expected verification: `python scripts/verify_phase_completion.py` if present
  - risk: scope outside files_allowed for this chunk

- [ ] T4
  - task: Fix Resolve UI + bridge contract so proposedAction and keeperLabel persist correctly after reload (`web/src/`, tests/contracts as needed)
  - files_allowed: .devtool/features/, scripts/, src/, web/src/
  - expected verification: `python scripts/verify_phase_completion.py` if present
  - risk: scope outside files_allowed for this chunk

- [ ] T5
  - task: Add regression test: approve exact group → preview → apply; assert keeper on disk, non-keepers under duplicate/ (`tests/` bridge or kiwi e2e)
  - files_allowed: .devtool/features/, scripts/, src/, web/src/
  - expected verification: `python scripts/verify_phase_completion.py` if present
  - risk: scope outside files_allowed for this chunk
