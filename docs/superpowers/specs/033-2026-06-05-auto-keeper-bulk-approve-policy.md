---
title: Auto-keeper + bulk approve policy (HITL)
status: locked
date: 2026-06-05
linear: NOV-32
parent_issue: NOV-31
related_issues:
  - NOV-16
  - NOV-19
  - NOV-33
  - NOV-34
  - NOV-35
plan: docs/superpowers/plans/033-2026-06-05-auto-keeper-bulk-approve-policy.md
---

# Auto-keeper + bulk approve policy (HITL)

## Summary (caveman)

- Lock auto-keeper + bulk approve for **unreviewed file rows** (exact, near, relation)
- Keeper: biggest size → newest mtime → path → file_id
- Keeper → approve+keep; non-keeper → approve+`move_duplicate`; conflict skipped
- Preview mandatory before apply; no checkbox; 500 cap chunked `current_query`
- Extends [NOV-16](https://linear.app/zkaufman/issue/NOV-16) `approved` semantics; impl in NOV-33/34/35

## Parent / program

- Parent: [NOV-31](https://linear.app/zkaufman/issue/NOV-31) — Resolve: auto-select keepers and approve unreviewed
- Supersedes exact-only bulk-approve assumptions from pre-NOV-32 work
- Builds on [NOV-16](https://linear.app/zkaufman/issue/NOV-16) (Done) execution-approved semantics

## Policy locks

```text
auto keeper selection: YES
move plan generation: YES (via preview)
immediate move without user confirm: NO
```

| Rule | Decision |
|------|----------|
| Selection scope | Active Resolve filter **plus** `filters.status: ["unreviewed"]` |
| Row types | **exact**, **near**, **relation** |
| Row granularity | **File rows only** (group header rows not mutated by bulk approve) |
| Keeper selection | Per duplicate group among current members: see tie-break below |
| Keeper on approve | `status=approved`, `proposedAction=keep` |
| Non-keeper on approve | `status=approved`, `proposedAction=move_duplicate`, `targetFolder=duplicate/` where applicable |
| Conflict | **Exclude** from selection (`status=conflict` never approved by bulk) |
| Cap | Max **500** file-row mutations per operation (`MAX_REVIEW_MUTATIONS`) |
| Chunking | Mirror bulk exclude: `current_query` with cursor offsets via `bulkMutationChunkCursors` |
| Preview gate | User must run move preview and confirm apply — **no** auto-apply after bulk approve |
| Selection UX | **No** checkbox revival ([NOV-19](https://linear.app/zkaufman/issue/NOV-19)); filter-driven `current_query` only |

## NOV-16 cross-reference (execution-approved)

From NOV-16 (locked):

```text
approved = execution-approved (ready for preview/apply)
approved ≠ already moved / executed
```

| Concept | NOV-16 (exact) | NOV-32 extension |
|---------|----------------|------------------|
| Auto-approve scope | Exact non-keeper members (scan hook) | User bulk approve: unreviewed **file** rows for exact+near+relation |
| Preview executable | `status=approved` AND `proposedAction=move_duplicate` | **Same** — near/relation non-keepers must use `move_duplicate` after bulk approve |
| Preview skip | excluded, conflict, keep, ignore | **Same** |
| Near/relation | Out of scope | **In scope** with mandatory preview (NOV-35 unblocks UI gate) |

Bulk approve sets `approved` on file rows; preview/apply semantics unchanged.

## Keeper tie-break (canonical)

Apply to **default keeper** when no valid persisted `keeper_file_id` override for the group:

1. **Largest** `size_bytes` (desc)
2. **Newest** `modified_at_ns` (desc) — field on `FileRecord`
3. **Stable path** — `relative_path` compared as POSIX-normalized string (asc)
4. **Stable id** — `file_id` asc (hex string compare)

**Override rule (unchanged from PR-17):** If stored `keeper_file_id` exists and is still a group member → use override; else recompute with tie-break above.

### Current code delta (pre-implementation)

| Location | Today | Target |
|----------|-------|--------|
| `duplicate_exact._pick_keeper` | `max(size_bytes, relative_path)` | Add `modified_at_ns` 2nd key; path/id 3rd/4th |
| `review_state_merge._pick_keeper_id` | Same tuple as exact | Align to canonical tie-break |
| `near_review_rows_builder` | `min(relative_path)` keeper; non-keeper `ignore` | Canonical tie-break; non-keeper `move_duplicate` |
| `relation_review_rows_builder` | Same as near | Same as near |
| `review_decisions.members_by_group` | Exact groups only | Extend to near/relation (NOV-33) |
| `_merge_non_exact_row` approved non-keeper | `proposedAction=ignore` | `proposedAction=move_duplicate` (NOV-33) |
| `previewEligibility.ts` | Blocks near/relation filters | Unblock after approve (NOV-35) |

## Per-type behavior

### Exact (`dup-*` groups)

| Phase | Behavior |
|-------|----------|
| Skeleton builder | `build_review_rows` + domain `find_exact_duplicate_groups` |
| Default keeper | Shared `_pick_keeper` / `_pick_keeper_id` updated to tie-break tuple |
| Non-keeper skeleton | `proposedAction=move_duplicate`, `targetFolder=duplicate/` |
| Bulk approve | Approve unreviewed file rows: keeper→keep, others→move_duplicate |
| Merge | `merge_review_state` exact branch (existing) |

### Near (`near:*` groups)

| Phase | Behavior |
|-------|----------|
| Skeleton builder | `build_near_review_rows` — **change** default keeper from `min(path)` to canonical tie-break |
| Non-keeper skeleton | Change default from `ignore` → `move_duplicate` + `targetFolder=duplicate/` for unreviewed |
| Bulk approve | Extend `UpdateReviewDecisionsUseCase` membership map to near groups |
| Merge | `_merge_non_exact_row` must set `proposedAction=move_duplicate` for approved non-keepers (not `ignore`) |

### Relation (`relation:*` groups)

Same as near, via `build_relation_review_rows` and relation group ids.

## Bulk approve command (semantic)

New user-facing action (UI label TBD in NOV-34): **approve filtered unreviewed** — mirrors `runBulkExcludeFiltered` structure.

```text
selection: { type: "current_query", query: { ...currentQuery, filters.status: ["unreviewed"], cursor } }
command: "approve"  # per-row: only file rows; conflict skipped server-side
```

Server responsibilities (NOV-33):

1. Resolve selection to file rows (cap 500).
2. Skip `status=conflict`.
3. For each file row, resolve `groupId` and group members (exact, near, or relation).
4. Compute effective keeper (override or tie-break).
5. Apply `approve` with effective `proposedAction` implied by keeper vs non-keeper (via merge rebuild or direct status+action fields).

**Do not** auto-run preview or apply.

## Conflict exclusion

- Rows with `status=conflict` are not selected by `filters.status: ["unreviewed"]`.
- Server MUST NOT promote conflict rows if filter bypassed.

## Cap and chunking

Reuse:

- `web/src/constants/reviewBulk.ts` — `bulkMutationTargetCount`, `bulkMutationChunkCursors`
- `src/application/review_decisions.py` — `MAX_REVIEW_MUTATIONS = 500`
- `selection_resolve` — `SELECTION_RESOLVE_ROW_CAP = 200` per chunk

## Preview-required gate

| Step | Required |
|------|----------|
| Bulk approve | Yes — sets execution-approved state |
| Build preview plan | Yes — user initiates |
| Apply moves | Yes — user confirms apply subflow |

`previewEligibility.ts` changes are **NOV-35** — must allow near/relation executable rows after bulk approve.

## Orthogonal: post-scan auto-approve

`review_auto_approve.persist_exact_non_keeper_approvals` remains **exact-only**, scan-time hook. Does not replace user bulk approve. If keeper tie-break changes, align this path to shared `_pick_keeper_id` helper.

## Code touch map (implementation — not NOV-32)

| Area | Path |
|------|------|
| Spec file | `docs/superpowers/specs/033-2026-06-05-auto-keeper-bulk-approve-policy.md` |
| Keeper helper | `src/domain/duplicate_exact.py`, `src/application/review_state_merge.py` (+ shared module) |
| Near/relation builders | `near_review_rows_builder.py`, `relation_review_rows_builder.py` |
| Mutations | `review_decisions.py` — near/relation `members_by_group` |
| UI bulk approve | `ResolveAndOrganizeWorkspace.tsx` |
| Preview gate | `previewEligibility.ts` (NOV-35) |

## Acceptance criteria mapping

| AC | Spec section |
|----|----------------|
| Policy table refs NOV-16 execution-approved | NOV-16 cross-reference |
| Exact/Near/Relation in scope; conflict excluded | Policy locks, per-type, conflict |
| Keeper tie-break documented | Keeper tie-break (canonical) |
| Preview-required gate explicit | Preview-required gate |
| Reviewer sign-off | Linear issue comment + human ack |

## Out of scope

- Library-wide unreviewed shortcut (no filter bypass)
- Step-through per-group wizard
- Auto-apply without preview
- Checkbox / explicit multi-select revival

## Downstream issues

| Issue | Delivers |
|-------|----------|
| [NOV-33](https://linear.app/zkaufman/issue/NOV-33) | Backend bulk approve + keeper tie-break + near/relation mutation |
| [NOV-34](https://linear.app/zkaufman/issue/NOV-34) | Confirm dialog + workspace wiring |
| [NOV-35](https://linear.app/zkaufman/issue/NOV-35) | Preview eligibility for near/relation after approve |

## Reviewer sign-off

- [ ] Human confirms policy table matches product intent
- [ ] Parent NOV-31 updated when all children locked

---

## Related Linear issues

| Issue | Role |
|-------|------|
| [NOV-16](https://linear.app/zkaufman/issue/NOV-16) | Execution-approved semantics (exact, Done) |
| [NOV-19](https://linear.app/zkaufman/issue/NOV-19) | No checkbox revival; filter-driven selection |
| [NOV-31](https://linear.app/zkaufman/issue/NOV-31) | Parent: auto-select keepers and approve unreviewed |
| [NOV-33](https://linear.app/zkaufman/issue/NOV-33) | Backend bulk approve mutation |
| [NOV-34](https://linear.app/zkaufman/issue/NOV-34) | Pre-approve confirm summary UX |
| [NOV-35](https://linear.app/zkaufman/issue/NOV-35) | Preview eligibility for near/relation |
