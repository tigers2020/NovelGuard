---
title: PR-17 Review State Persistence
status: approved
date: 2026-06-01
parent_spec: docs/superpowers/specs/002-2026-06-01-novelguard-greenfield-library-session-design.md
related_specs:
  - docs/superpowers/specs/000-2026-06-01-novelguard-ui-overhaul-design.md
  - docs/superpowers/specs/001-2026-06-01-pr13-preview-token-stale-apply-design.md
  - docs/superpowers/specs/003-2026-06-01-real-apply-use-cases-design.md
  - docs/superpowers/specs/004-2026-06-01-resolve-ui-apply-outcome-design.md
plan: docs/superpowers/plans/011-2026-06-01-pr17-review-state-persistence.md
---

# PR-17: Review State Persistence

## Goal

Persist user review decisions for exact-duplicate **Resolve & Organize** rows: **keeper choice**, **approved / excluded / conflict** status, and **truthful aggregate counts** on `AppSnapshot` and `ReviewRowsPage`. Enable batch **선택 승인** / **선택 제외** (currently stubbed in UI). Survive session restarts and post-apply index refresh by merging stored decisions with re-detected duplicate groups.

PR-14 left every row `"unreviewed"` and snapshot `approvedCount` / `conflictCount` at zero ([002 greenfield § Review rows](./002-2026-06-01-novelguard-greenfield-library-session-design.md)). PR-16 deferred per-row post-apply grid status ([004 resolve UI](./004-2026-06-01-resolve-ui-apply-outcome-design.md)).

## Position in program

| PR | Delivers |
|----|----------|
| PR-14b | Exact duplicate rows + SQLite file index |
| PR-15 | Real `move_duplicate` apply + refresh-from-disk |
| PR-16 | Apply subflow outcome UI |
| **PR-17** | **Persisted review state + snapshot truth + batch approve/exclude** |
| PR-18 | Rich `getDuplicateGroupDetail` + keeper picker in detail (may extend PR-17 UI) |

Wave B per [master roadmap](../roadmap/000-2026-06-01-novelguard-master-roadmap.md).

---

## In scope

| Area | Behavior |
|------|----------|
| Persistence | SQLite (same DB as `files`) stores per-group keeper override and per-row review status |
| Merge on rebuild | After scan / `refresh_index_from_disk`, re-apply stored decisions to newly built review cache |
| Bridge command | `updateReviewDecisions` — batch mutations scoped by `SelectionScope` |
| Snapshot | `work.resolve.approvedCount`, `conflictCount`, `queueCount` derived from persisted state |
| Page summary | `ReviewRowsPage.summary` counts reflect merged row `status` (already implemented in `review_query.py`; inputs become non-zero) |
| UI | Enable `BatchActionBar` approve / exclude; refresh grid + snapshot after mutations |
| Post-apply | **No** review DB writes on apply success — `refresh_index_from_disk` rebuilds rows; moved files leave duplicate groups (grill-me lock B) |
| Preview safety | Review mutations that change executable plan → bump `libraryRevision`, clear pending preview (PR-13) |
| mockBridge | Parity for `updateReviewDecisions` in browser dev |

## Out of scope

| Item | Owner |
|------|--------|
| Near / relation / `move_only` row types | PR-19+ |
| Full duplicate group detail panel + member picker UX polish | PR-18 (PR-17 may add minimal keeper change API only) |
| Target folder editing / `move_organized` | Future |
| Automatic conflict detection from encoding/integrity analyzers | Future (PR-17 supports **manual** `markConflict` only) |
| New test files without `TEST_ALLOWED` | Plan uses existing contract / E2E / mock parity only |
| Quality workspace review state | PR-21+ |
| Delete / trash actions | Later waves |

---

## Current baseline (code truth)

| Item | Today |
|------|--------|
| `build_review_rows` | All rows `status: "unreviewed"`; keeper from `_pick_keeper` only |
| `build_snapshot` | `resolve.conflictCount` / `approvedCount` hard-coded `0` |
| `BatchActionBar` | Approve / exclude disabled with stub tooltip |
| `NovelGuardBridge` | No review-mutation method |
| SQLite | `files`, `quality_issues` only — no review tables |
| `_rebuild_review_index` | Replaces cache; **drops** any in-memory review intent |
| mockBridge | Random statuses in `mockData` only (not persisted) |

Row ids (stable across rebuild when group membership unchanged):

```text
group:{groupId}           # e.g. group:dup-abc123...
file:{groupId}:{fileId}   # file id = FileRecord.id (content-addressed path hash)
```

`groupId` = `dup-{content_sha256[:16]}` from [duplicate_exact.py](../../../src/domain/duplicate_exact.py).

---

## Review state model

### Status enum (unchanged contract)

`ReviewStatus` = `"unreviewed" | "approved" | "conflict" | "excluded"` ([review.ts](../../../web/src/types/review.ts)).

### Persistence granularity

| Entity | Key | Stored fields |
|--------|-----|----------------|
| Duplicate group | `group_id` (string) | `keeper_file_id` (optional override), `group_status` (optional) |
| File member | `file_id` (string) | `member_status` (optional override) |

**Effective row status** when building cache:

1. If `member_status` set → use it for file rows.
2. Else if `group_status` set → file rows inherit except rows with explicit `member_status`.
3. Else → `"unreviewed"`.
4. Group header row: `group_status` if set, else `"unreviewed"`.

### Keeper override

- Default keeper: domain `_pick_keeper` (largest size, then path).
- User `setKeeper` stores `keeper_file_id` for `group_id`; must be a current group member.
- On merge, if stored `keeper_file_id` is **not** in current group members → **ignore override**, use `_pick_keeper`; prune orphan keeper row (grill-me lock A).
- Rebuild recomputes `keeperLabel`, `proposedAction`, `targetFolder` from effective keeper:
  - Keeper file: `proposedAction: "keep"`, `targetFolder: null`
  - Others: `proposedAction: "move_duplicate"`, `targetFolder: "duplicate/"` (unchanged v1 convention)

### Approve / exclude semantics

| Command | Selection resolves to | Effect |
|---------|----------------------|--------|
| `approve` | Group rows | Set `group_status = approved` for that `groupId` |
| `approve` | File rows only | Set `member_status = approved` for each file |
| `exclude` | Group or file | `excluded` at same granularity |
| `setKeeper` | Exactly one file row (or one group + `keeperFileId`) | Set `keeper_file_id`; **only** rows with `approved` → `unreviewed` (plan changed); `excluded` / `conflict` unchanged |
| `markConflict` | Group or file | `conflict` at same granularity |
| `reset` | **Group** row / `group:` id | Clear `group_status` **and** `keeper_file_id` for that `group_id` (grill-me lock C) |
| `reset` | **File** row only | Clear `member_status` only; **keeper override unchanged** |

**Group approve** does not auto-approve excluded members (explicit `member_status` wins).

### Conflict rules (v1)

- `markConflict` is user-driven only (no heuristic).
- `setKeeper` on a group with `group_status: approved` → `group_status` becomes `unreviewed`; file members: **only** `approved` (explicit or inherited) → `unreviewed`; `excluded` / `conflict` **unchanged** (grill-me lock A).
- Invalid `keeperFileId` (not in group) → bridge error `INVALID_REVIEW_COMMAND`; no partial write.

### Queue count (snapshot)

**Scope (grill-me lock A):** aggregates over **all** exact-duplicate **file** rows in the session cache — **not** the current grid filter / `viewMode`. `ReviewRowsPage.summary` remains filter-local (existing `review_query.py` behavior).

```text
queueCount = count(file rows where status in ("unreviewed", "conflict"))
```

Group header rows are **not** counted in `queueCount` (action queue = file-level work items).

```text
approvedCount = count(file rows where status == "approved")
conflictCount   = count(file rows where status == "conflict")
```

`get_snapshot` / `build_snapshot` use session-wide aggregates; mockBridge aligns (library-wide `summarizeReviewRows`).

---

## Persistence schema (SQLite)

Additive migration on existing library DB (`SqliteLibraryIndex`):

```sql
CREATE TABLE IF NOT EXISTS review_group_state (
  folder_path TEXT NOT NULL,
  group_id TEXT NOT NULL,
  keeper_file_id TEXT,
  group_status TEXT,
  updated_at TEXT NOT NULL,
  PRIMARY KEY (folder_path, group_id)
);

CREATE TABLE IF NOT EXISTS review_member_state (
  folder_path TEXT NOT NULL,
  file_id TEXT NOT NULL,
  member_status TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  PRIMARY KEY (folder_path, file_id)
);

CREATE INDEX IF NOT EXISTS idx_review_group_folder ON review_group_state(folder_path);
CREATE INDEX IF NOT EXISTS idx_review_member_folder ON review_member_state(folder_path);
```

**Lifecycle:**

| Event | Review tables |
|-------|----------------|
| `select_folder` (new library) | `DELETE` all rows for previous folder; empty for new folder |
| `replace_files` / rescan | Keep rows for `folder_path`; merge at cache build |
| `clear()` on index | Delete review rows for cleared folder |

Orphan cleanup: on merge, ignore `review_*` rows whose `group_id` / `file_id` no longer exist in the current index (no error).

**Port:** extend `LibraryIndexPort` with load/save review state — implementation in `SqliteLibraryIndex`; in-memory index implements no-op or dict backing for tests.

---

## Merge algorithm (application)

After `find_exact_duplicate_groups` + `build_review_rows` skeleton:

```text
load review_group_state, review_member_state for folder_path
for each built row:
  if row is group header:
    apply group_status, keeper override → recompute keeperLabel / actions for group row
  if row is file member:
    apply keeper override + member_status
recompute snapshot aggregates from file rows
```

`build_review_rows` remains pure-ish; **`merge_review_state(rows, stored, files_by_id)`** lives in `application/` (not domain).

---

## Bridge contract

### New command

```typescript
type ReviewDecisionCommand =
  | "approve"
  | "exclude"
  | "setKeeper"
  | "markConflict"
  | "reset";

interface UpdateReviewDecisionsRequest {
  selection: SelectionScope;
  command: ReviewDecisionCommand;
  /** Required when command === "setKeeper" and selection is group-level */
  keeperFileId?: string;
}

interface UpdateReviewDecisionsResult {
  updatedCount: number;
  libraryRevision: number;
}
```

| Method | Kind | Notes |
|--------|------|-------|
| `updateReviewDecisions(request)` | command | Validates `SelectionScope`, applies batch, returns result |

Add to `NOVEL_GUARD_BRIDGE_METHODS`, `NovelGuardBridge`, `BridgeApi`, `mockBridge`, `pywebviewBridge`, Python `bridge_parity`.

### Validation

- Reuse PR-10 `validateSelectionScope` / Python mirror.
- Resolve selection to concrete row ids against **current** `_review_rows_cache` (same helper family as apply preview).
- `limit` on mutation batch: **max 500 row ids** per call (guardrail).
- Empty selection → `updatedCount: 0`, no error.
- Batch UI (PR-17) sends **`explicit_rows` only**; server may still accept `current_query` for tests/API parity, but web batch actions must not use it without future confirm flow.

### Errors

New code in existing bridge error module (no new error transport shape):

| Code | When |
|------|------|
| `INVALID_REVIEW_COMMAND` | Bad keeper, unknown command, setKeeper without file id |
| `LIBRARY_BUSY` | Scan or apply in progress (same as apply) |

### Revision + pending preview

On any mutation with `updatedCount > 0` (**grill-me lock A** — all commands: `approve`, `exclude`, `setKeeper`, `markConflict`, `reset`):

```text
1. increment libraryRevision once
2. discard pending preview (previewToken cleared, hasPendingApply = false)
3. rebuild review cache rows in memory from index + persisted state (no full rescan)
```

No command is exempt from revision bump or preview discard in PR-17.

UI: existing stale banner / refresh snapshot hook.

---

## Interaction with apply (PR-15)

After `applyResolvedActions` with ≥1 successful `move_duplicate` (PR-15 already calls `refresh_index_from_disk`):

| Outcome | Review state (grill-me lock B) |
|---------|------------------------------|
| File moved away | Rebuild drops row from cache; **prune** orphan `review_member_state` / `review_group_state` for ids no longer in index (same as rescan orphan cleanup) |
| Keeper moved | Re-resolve keeper from persisted override or `_pick_keeper` on remaining members after rebuild |
| Post-apply `approved` write | **None** — queue/count updates come from fewer duplicate rows, not status flip |

Per-row post-apply grid status (PR-16 deferral) remains **out of scope**; optional transient UI → PR-18+.

Does **not** change PR-15 plan fingerprint rules; user must re-preview after review edits **before** apply (revision bump enforces stale path).

### Preview / apply planner filter (grill-me lock A)

`BuildPreviewPlanUseCase` / apply execution (same row filter) for **file** rows:

| `status` | In executable `move_duplicate` plan? |
|----------|--------------------------------------|
| `unreviewed` | Yes (if `proposedAction === "move_duplicate"`) |
| `approved` | **No** — treat as reviewed; skip (not `blockedCount`) |
| `excluded` | **No** — skip (not `blockedCount`) |
| `conflict` | **No** — skip until user clears conflict (`reset` / approve) |

Group header rows (`rowKind: "group"`) remain non-executable (existing PR-15 behavior).

Status is authoritative over stale `proposedAction` in cache after merge.

---

## UI (web)

| Component | PR-17 change |
|-----------|----------------|
| `BatchActionBar` | Wire **선택 승인** / **선택 제외** → `updateReviewDecisions` with **`explicit_rows` only** |
| `BatchActionBar` enablement | **Locked (grill-me):** buttons enabled only when `explicitIds.length >= 1`; disabled + tooltip when zero — **no** `current_query` whole-filter approve in PR-17 |
| `ResolveAndOrganizeWorkspace` | Pass `{ type: "explicit_rows", rowIds: explicitIds }` to batch commands; on success call `useRefreshSnapshot` + reload `queryReviewRows` |
| `DetailPanel` | Read-only keeper (grill-me lock A); no `markConflict` / `reset` / `setKeeper` buttons in PR-17 |
| Other review commands | `markConflict`, `reset`, `setKeeper` — **bridge API + contract tests** only until PR-18 |
| Stat chips | Show non-zero `approvedCount` / `conflictCount` from snapshot |

Korean labels unchanged (presentation layer).

---

## Layering

| Layer | Responsibility |
|-------|----------------|
| `domain` | No persistence; optional pure helper for proposedAction from keeper |
| `application` | `UpdateReviewDecisionsUseCase`, `merge_review_state`, snapshot aggregate helper |
| `infrastructure` | SQLite CRUD for `review_*` tables |
| `app` | `BridgeApi.update_review_decisions` — validate DTO, delegate |
| `web` | Types, bridge wiring, BatchActionBar |

---

## Tests and verification

Extend **existing** files only (no new test modules without approval):

| Area | File |
|------|------|
| Python contract | `tests/test_bridge_contract.py` — approve persists, snapshot counts, merge after rebuild |
| Bridge parity | `web/src/contracts/bridgeParity.ts`, `bridgeParity.test.ts` |
| mockBridge | Approve/exclude updates in-memory store |
| E2E (optional) | `web/e2e/smoke.spec.ts` — enable batch approve if stable; else manual smoke in plan |

Gate: `python scripts/verify_phase_completion.py`

Manual smoke:

1. Scan folder with duplicate pair → rows `unreviewed`, snapshot counts 0 / queue > 0.
2. Select member → **선택 승인** → status `approved`, snapshot `approvedCount` increments.
3. Preview → apply move → post-apply row approved or removed; counts updated.
4. Rescan / refresh → decisions survive for unchanged `groupId` / `file_id`.

---

## Non-goals (PR-17)

- PR-18 detail panel member list / keeper radio UI (API ready; UI can follow in 18)
- Near/relation duplicate review
- Undo review decisions (reset command is v1 undo)
- Syncing review state to audit JSONL
- Cross-folder review state

---

## PR-18 boundary

| Concern | PR-17 | PR-18 |
|---------|-------|-------|
| Persist keeper / status | Yes | Consumes |
| `getDuplicateGroupDetail` richness | Unchanged stub OK | Yes |
| Detail panel keeper picker | Optional minimal | Full UX |

---

## Approval checklist

- [x] Persistence: SQLite `review_group_state` + `review_member_state` on same DB as files
- [x] Merge after scan/refresh; orphan cleanup; stale `keeper_file_id` → ignore (grill-me)
- [x] `updateReviewDecisions` + `SelectionScope` + command table (incl. reset C)
- [x] Revision bump + discard preview on **all** commands (grill-me A)
- [x] Post-apply: no review DB write; refresh + orphan prune only (grill-me B)
- [x] Snapshot library-wide file-row aggregates (grill-me A)
- [x] Batch: explicit selection only; approve/exclude UI only (grill-me A)
- [x] Preview/apply skip `approved` / `excluded` / `conflict` rows (grill-me A)
- [x] setKeeper clears **approved** only (grill-me A)
- [ ] Test strategy (extend existing files only) — default accepted unless object
- [x] **Human sign-off:** spec + plan approved; implemented 2026-06-01

**After approval:** implement per [011 plan](../plans/011-2026-06-01-pr17-review-state-persistence.md).

### Grill-me decision log (2026-06-01)

| # | Topic | Lock |
|---|--------|------|
| 1 | Batch approve/exclude | Explicit row selection required (B) |
| 2 | setKeeper downgrade | Approved → unreviewed only (A) |
| 3 | Preview invalidation | All commands bump revision + discard preview (A) |
| 4 | Post-apply state | No DB write; refresh + prune (B) |
| 5 | Stale keeper_file_id | Ignore → `_pick_keeper` (A) |
| 6–7 | Preview planner | Skip approved / excluded / conflict (A) |
| 8 | reset | Group: keeper+status; file: member_status only (C) |
| 9 | Snapshot counts | Library-wide file rows (A) |
| 10 | PR-17 UI | Batch approve/exclude only; other commands API-only (A) |

---

## Changelog

| Date | Change |
|------|--------|
| 2026-06-01 | Initial PR-17 spec draft (Wave B) |
| 2026-06-01 | Grill-me: batch approve/exclude require explicit row selection (option B) |
| 2026-06-01 | Grill-me: setKeeper clears approved only; excluded/conflict preserved (option A) |
| 2026-06-01 | Grill-me: every review command bumps revision + discards preview (option A) |
| 2026-06-01 | Grill-me: no post-apply approved write; refresh + orphan prune only (option B) |
| 2026-06-01 | Grill-me: stale keeper_file_id ignored → _pick_keeper; prune orphan (option A) |
| 2026-06-01 | Grill-me: preview/apply skip excluded + approved file rows (option A) |
| 2026-06-01 | Grill-me: preview/apply skip conflict file rows until cleared (option A) |
| 2026-06-01 | Grill-me: reset group clears keeper+status; reset file clears member_status only (option C) |
| 2026-06-01 | Grill-me: snapshot resolve counts = library-wide file rows (option A) |
| 2026-06-01 | Grill-me: PR-17 UI = batch approve/exclude only; markConflict/reset/setKeeper API-only (option A) |
