# PR-17: Review State Persistence — Implementation Plan

> **For agentic workers:** Use superpowers:subagent-driven-development or superpowers:executing-plans. Track steps with `- [ ]` checkboxes.

**Goal:** Persist keeper and review status for exact-duplicate rows; expose `updateReviewDecisions`; make snapshot and page summaries truthful; enable batch approve/exclude in Resolve UI.

**Architecture:** SQLite tables `review_group_state` / `review_member_state` on existing library DB. Application `merge_review_state` overlays persisted decisions when building `_review_rows_cache`. `UpdateReviewDecisionsUseCase` resolves `SelectionScope`, writes DB, rebuilds cache aggregates, bumps revision, clears pending preview. Bridge stays thin.

**Tech Stack:** Python 3.12 (`domain` / `application` / `infrastructure` / `app`), React + existing PR-10 DTOs, Vitest + pytest (extend existing files only).

**Spec:** [005-2026-06-01-review-state-persistence-design.md](../specs/005-2026-06-01-review-state-persistence-design.md) (**approved** 2026-06-01)

**Plan status:** **Implemented** (2026-06-01) — Tasks 1–9 complete; verification PASS.

**Parent:** [000 master roadmap](../roadmap/000-2026-06-01-novelguard-master-roadmap.md) — Wave B PR-17

**Depends on:** PR-14b (review rows), PR-15 (apply + refresh), PR-16 (apply UI — recommended)

**Test policy:** No new `test_*.py` / `*.test.tsx` without `TEST_ALLOWED`. Extend:

- `tests/test_bridge_contract.py`
- `web/src/contracts/bridgeParity.ts` + `bridgeParity.test.ts`
- `web/src/bridge/mockBridge.ts` (in-memory review store)
- `web/e2e/smoke.spec.ts` only if stable (optional Task 8)

---

## Plan-locked decisions

| Lock | Value |
|------|--------|
| Storage | Same SQLite file as `files`; new tables per spec § schema |
| Row keys | `group_id`, `file_id` (FileRecord.id) — not display row id strings in DB |
| Bridge method | Single `updateReviewDecisions` command |
| Mutation cap | 500 row ids per request |
| Revision | `increment_library_revision()` once when `updatedCount > 0` |
| Pending preview | Clear on review mutation (same as spec) |
| Post-apply | **No** review DB write on apply; prune orphans after `refresh_index_from_disk` only (grill-me B) |
| queueCount | File rows with `unreviewed` or `conflict` only |
| Detail keeper UI | Read-only OK in PR-17; `setKeeper` via API for PR-18 / tests |
| Batch approve/exclude | **explicit_rows only**; buttons disabled when `explicitIds.length === 0` (grill-me lock) |
| setKeeper downgrade | Clear **approved** only; preserve `excluded` / `conflict` (grill-me lock A) |
| Preview invalidation | **All** review commands → revision++ + discard pending preview (grill-me lock A) |
| Stale keeper_file_id | Ignore override → `_pick_keeper`; prune orphan DB row (grill-me A) |
| Preview planner | Skip file rows with `status` in `approved`, `excluded`, `conflict` (grill-me A) |
| reset command | Group → clear keeper + status; file → `member_status` only (grill-me C) |
| Snapshot counts | Library-wide file-row aggregates (not current filter) (grill-me A) |
| PR-17 web UI | Batch approve/exclude only; other commands API/contract only (grill-me A) |

---

## Current state (baseline)

| Item | Status |
|------|--------|
| Review persistence | **Missing** |
| `build_snapshot` resolve counts | Hard-coded `0` |
| `BatchActionBar` approve/exclude | Disabled stub |
| `NovelGuardBridge` | No `updateReviewDecisions` |
| `_rebuild_review_index` | Loses user intent every scan/refresh |
| PR-15 apply hook | No review state update after move |

---

## File map

| File | Action |
|------|--------|
| `src/infrastructure/sqlite_library_index.py` | **Modify** — schema + CRUD review tables |
| `src/infrastructure/memory_library_index.py` | **Modify** — in-memory review dict for tests |
| `src/application/ports/library_index.py` | **Modify** — review state port methods |
| `src/application/review_state_merge.py` | **Create** — `merge_review_state(rows, stored, files_by_id)` |
| `src/application/review_decisions.py` | **Create** — `UpdateReviewDecisionsUseCase` |
| `src/application/review_snapshot_counts.py` | **Create** — aggregate helpers for snapshot |
| `src/application/library_session.py` | **Modify** — merge on rebuild; expose mutation; snapshot counts |
| `src/application/dto_mapper.py` | **Modify** — pass real `approvedCount` / `conflictCount` / `queueCount` |
| `src/application/review_rows_builder.py` | **Modify** — optional: accept keeper override input |
| `src/app/bridge_api.py` | **Modify** — `update_review_decisions` |
| `src/app/bridge_contract.py` | **Modify** — validate request/result; `INVALID_REVIEW_COMMAND` |
| `src/app/bridge_parity.py` | **Modify** — method list |
| `src/app/build_preview_plan.py` | **Modify** — skip non-executable review statuses |
| `src/app/apply_resolved_actions.py` | **Modify** — same status filter + orphan prune after refresh |
| `src/app/selection_resolve.py` (or existing helper) | **Modify** — reuse for review selection |
| `web/src/types/review.ts` | **Modify** — request/result types |
| `web/src/contracts/bridgeParity.ts` | **Modify** — `updateReviewDecisions` |
| `web/src/bridge/NovelGuardBridge.ts` | **Modify** |
| `web/src/bridge/pywebviewBridge.ts` | **Modify** |
| `web/src/bridge/mockBridge.ts` | **Modify** — persisted in-memory review |
| `web/src/features/work/resolve/BatchActionBar.tsx` | **Modify** — wire buttons |
| `web/src/features/work/ResolveAndOrganizeWorkspace.tsx` | **Modify** — selection scope + refresh |
| `tests/test_bridge_contract.py` | **Extend** |
| `docs/entry_points.md` | **Modify** — PR-17 bridge method |
| `docs/superpowers/roadmap/000-…-master-roadmap.md` | **Modify** on completion — PR-17 done |

---

## Acceptance criteria

```text
✓ updateReviewDecisions(approve) persists; queryReviewRows shows approved status
✓ getSnapshot resolve.approvedCount / conflictCount / queueCount match file-row aggregates
✓ setKeeper updates keeperLabel + proposedAction; invalid keeper → INVALID_REVIEW_COMMAND
✓ Rescan / refresh_index_from_disk preserves decisions for stable group_id + file_id
✓ Review mutation increments libraryRevision and clears pending preview
✓ Post-apply: orphan review state pruned after refresh; no member_status=approved write on apply
✓ BatchActionBar approve/exclude enabled and calls bridge
✓ BridgeApi: no business logic beyond validate + delegate
✓ python scripts/verify_phase_completion.py PASS
✓ Manual smoke checklist signed off (Task 9)
```

---

## Commit strategy (recommended)

| Commit | Content |
|--------|---------|
| `[docs] PR-17 review state spec and plan` | Spec 005 + this plan |
| `[infra] sqlite review state tables` | Tasks 1–2 |
| `[app] merge review state into review cache` | Task 3 |
| `[app] updateReviewDecisions use case + bridge` | Tasks 4–5 |
| `[app] post-apply review status + snapshot counts` | Task 6 |
| `[web] batch approve exclude + bridge types` | Task 7 |
| `[tests] PR-17 review persistence contract` | Task 8 |
| `[docs] mark PR-17 complete` | Task 9 |

---

### Task 1: SQLite schema + port

**Files:** `sqlite_library_index.py`, `library_index.py`, `memory_library_index.py`

- [ ] **Step 1:** Add `review_group_state` / `review_member_state` tables and indexes per spec.
- [ ] **Step 2:** Implement `load_review_state(folder_path)`, `upsert_group_state`, `upsert_member_state`, `delete_review_state_for_folder`, `prune_orphans` (or lazy ignore on read).
- [ ] **Step 3:** Wire `clear()` / `replace_files` to retain or clear per spec lifecycle.
- [ ] **Step 4:** Run `pytest tests/test_bridge_contract.py -q` (existing pass baseline).

---

### Task 2: `merge_review_state`

**Files:** `review_state_merge.py`, `review_rows_builder.py` (if needed)

- [ ] **Step 1:** Implement merge: keeper override → recompute `proposedAction` / `targetFolder` / `keeperLabel`.
- [ ] **Step 2:** Apply `group_status` / `member_status` precedence rules from spec.
- [ ] **Step 3:** Unit-level checks via bridge contract tests (no new test file).

---

### Task 3: LibrarySession integration

**Files:** `library_session.py`, `dto_mapper.py`, `review_snapshot_counts.py`

- [ ] **Step 1:** In `_rebuild_review_index`, after `build_review_rows`, call `merge_review_state` with loaded DB state.
- [ ] **Step 2:** Compute `_queue_count`, `_approved_count`, `_conflict_count` from file rows; pass to `build_snapshot`.
- [ ] **Step 3:** Fix `dto_mapper.build_snapshot` to use parameters instead of literal `0`.
- [ ] **Step 4:** `select_folder` clears review state for switched library.

---

### Task 4: `UpdateReviewDecisionsUseCase`

**Files:** `review_decisions.py`, selection helper, `preview_apply_guard.py` (discard)

- [ ] **Step 1:** Resolve `SelectionScope` → row ids (reuse apply selection resolver).
- [ ] **Step 2:** Implement commands: `approve`, `exclude`, `setKeeper`, `markConflict`, `reset`.
- [ ] **Step 3:** Persist to index port; rebuild cache; return `{ updatedCount, libraryRevision }`.
- [ ] **Step 4:** Reject when `is_apply_or_scan_busy()` → `LIBRARY_BUSY`.
- [ ] **Step 5:** On success: `increment_library_revision`, `discard` pending preview, `set_has_pending_apply(false)`.

---

### Task 5: Bridge + contract

**Files:** `bridge_api.py`, `bridge_contract.py`, `bridge_parity.py`

- [ ] **Step 1:** Add `update_review_decisions` + JSON wrapper if pattern exists.
- [ ] **Step 2:** Validate request shape; validate result shape.
- [ ] **Step 3:** Extend `tests/test_bridge_contract.py` — approve + snapshot counts + invalid keeper.

---

### Task 6: Post-apply orphan prune

**Files:** `apply_resolved_actions.py`, `library_session.py`, `sqlite_library_index.py`

- [ ] **Step 1:** After `refresh_index_from_disk`, prune `review_*` rows whose `group_id` / `file_id` are absent from current index (no `approved` write on apply).
- [ ] **Step 2:** Recompute snapshot counts from rebuilt cache.

---

### Task 7: Web UI + bridge types

**Files:** `review.ts`, `NovelGuardBridge.ts`, `pywebviewBridge.ts`, `mockBridge.ts`, `BatchActionBar.tsx`, `ResolveAndOrganizeWorkspace.tsx`

- [ ] **Step 1:** Add TS types + `NOVEL_GUARD_BRIDGE_METHODS` entry.
- [ ] **Step 2:** `mockBridge` — in-memory review map keyed like SQLite; parity with Python semantics.
- [ ] **Step 3:** Enable batch buttons; pass `SelectionScope` from workspace selection state.
- [ ] **Step 4:** On success: refresh snapshot + reload current `queryReviewRows` page.
- [ ] **Step 5:** `npm run lint` + contract tests in `web/`.

---

### Task 8: Contract / parity tests

**Files:** `bridgeParity.ts`, `bridgeParity.test.ts`, `test_bridge_contract.py`

- [ ] **Step 1:** Parity list includes `updateReviewDecisions`.
- [ ] **Step 2:** Python: temp session with duplicate fixture → approve → assert counts.
- [ ] **Step 3:** Optional E2E: click `batch-approve` when selection present — skip if flaky; document in Task 9.

---

### Task 9: Verification + docs

- [ ] **Step 1:** `python scripts/verify_phase_completion.py` — record pass/fail counts.
- [ ] **Step 2:** Manual smoke (spec § Tests).
- [ ] **Step 3:** Update `docs/entry_points.md` and master roadmap PR-17 → Done.
- [ ] **Step 4:** Set spec `status: approved` and plan checkboxes when slice closed.

**Manual smoke checklist:**

```text
[ ] Scan dup folder → unreviewed rows, approvedCount=0
[ ] Select rows → 선택 승인 → approved status + snapshot bump
[ ] Preview → apply → post-apply state sane
[ ] Rescan → decisions survive for same content hash group
[ ] setKeeper via contract test / API — invalid id rejected
```

---

## Risks

| Risk | Mitigation |
|------|------------|
| `groupId` changes if hash algorithm changes | Document stability; migration out of scope |
| Large batch approve | 500 cap + SelectionScope already bounded by query |
| E2E selection wiring | Optional E2E; contract tests primary |
| PR-18 overlaps detail UI | Spec boundary: read-only detail OK |

---

## Changelog

| Date | Change |
|------|--------|
| 2026-06-01 | Initial PR-17 implementation plan (draft) |
