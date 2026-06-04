---
id: pr-58-exact-keeper-move-2026-06-04-spec-draft
status: spec-review
work_id: pr-58-exact-keeper-move-2026-06-04
linked_inbox: .devtool/features/done/pr-58-exact-keeper-move-2026-06-04-inbox.md
acceptance: "After approving an exact duplicate group (>=2 members), preview/apply moves every non-keeper to duplicate/ while the keeper path stays on disk; Resolve rows show keep vs move_duplicate consistently after reload; regression test (bridge or kiwi e2e) covers approve -> preview -> apply."
files_allowed: null
automation_state: approved
approved: true
approved_by: kanban_automation
approved_at: auto
---

# [Spec Draft] pr-58-exact-keeper-move-2026-06-04

## Problem

Exact (type exact) duplicate files should leave one copy in the library and move the rest to duplicate/, but the app is not doing so end-to-end.

| Field | Value |
|-------|-------|
| **Track** | resolve |

## Scope

User report: exact duplicate files should leave one keeper in the library and move the rest to duplicate/. Investigate approve, review state merge, preview selection, and apply paths: review_rows_builder, review_state_merge, reconcile_approved_duplicate_proposed_actions, build_preview_plan. Reproduce: scan with byte-identical files, approve exact group in Resolve, preview, apply. Near/relation policy unchanged unless required for exact parity.

## Acceptance criteria

After approving an exact duplicate group (>=2 members), preview/apply moves every non-keeper to duplicate/ while the keeper path stays on disk; Resolve rows show keep vs move_duplicate consistently after reload; regression test (bridge or kiwi e2e) covers approve -> preview -> apply.

## files_allowed proposal

- src/
- web/src/
- tests/
- scripts/
- .devtool/features/

## Goals

- Exact duplicate approve → preview → apply moves non-keepers to duplicate/ and keeps one keeper on disk.
- Resolve UI rows match backend proposedAction after reload.

## Non-goals

- Near/relation duplicate policy changes unless required for exact parity.
- Product-code implementation during planning automation.

## Decisions

- Fix keeper vs move_duplicate in review merge and preview plan selection first, then UI parity.

## UX impact

- Resolve grid must show keep vs move_duplicate consistently after reload.

## Backend impact

- review_state_merge, reconcile_approved_duplicate_proposed_actions, build_preview_plan.

## Safety impact

- Apply must not delete keeper; non-keepers go to duplicate/ only.
