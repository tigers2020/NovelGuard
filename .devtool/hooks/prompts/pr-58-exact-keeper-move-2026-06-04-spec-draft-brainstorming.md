/caveman

You are working on NovelGuard.

/brainstorming

Goal:
Turn the Inbox card into a Spec Draft card.

Rules:
- Follow AGENTS.md and docs/agent/KANBAN-detail.md.
- This is planning only. Do not edit product code.
- Edit only this target card: .devtool/features/pr-58-exact-keeper-move-2026-06-04-spec-draft.md
- Do not delete or move audit cards.
- Do not create test files.
- Use snake_case for variables if code examples are unavoidable.
- Korean comments only if code comments are unavoidable.

Inputs:
- Inbox card: .devtool/features/pr-58-exact-keeper-move-2026-06-04-spec-draft.md
- work_id: pr-58-exact-keeper-move-2026-06-04-spec-draft
- files_allowed proposal: .devtool/features/, scripts/, src/, web/src/
- acceptance: See source Inbox card.

Write the target Spec Draft card with:
- Problem
- Goals
- Non-goals
- Decisions
- UX impact
- Backend impact
- Safety impact
- Acceptance criteria
- files_allowed proposal

Inbox body:
# [Spec Draft] pr-58-exact-keeper-move-2026-06-04

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
