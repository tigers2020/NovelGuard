---
title: Resolve bulk auto-select/approve — server-side job with full-filter summary and progress
status: contract-review
date: 2026-06-05
implementation: not-on-main
implementation_branch: feature/resolve-bulk-auto-approve-job
contract_pr: pending
risk: safe
kind: feature
layer: crosslayer
area: work
tags:
  - resolve
  - bulk-approve
  - auto-keeper
  - background-job
  - large-library
related_specs:
  - docs/superpowers/specs/033-2026-06-05-auto-keeper-bulk-approve-policy.md
  - docs/superpowers/specs/034-2026-06-05-infra-large-library-loading-stability-design.md
  - docs/adr/NOV-32-auto-keeper-policy.md
---

> **Status:** `contract-review` / **not implemented** on `main`
> **Implementation branch (planned):** `feature/resolve-bulk-auto-approve-job` — **do not code until this contract PR merges**
> **Current main contract:** [main-ux-contract.md](../../architecture/main-ux-contract.md) — Work 3-mode + subflow dialogs
> **Prerequisites met:** PR #59 (IA contract), PR #60–#61 (036 done). Stabilization closed.
> **Policy authority:** [033 auto-keeper bulk approve policy](./033-2026-06-05-auto-keeper-bulk-approve-policy.md) remains locked; this spec defines the **server-job delivery** slice.

# Resolve bulk auto-select/approve — server-side job

## Summary

Replace the client-driven chunked bulk approve flow with a **server-authoritative background job** for Resolve **미검토 자동 선정·승인**.

User outcome: one click on the current filter processes **all** unreviewed file rows without grid preload, without repeated bridge chunk loops, and without exposing the public `MAX_REVIEW_MUTATIONS = 500` cap in the bulk UX.

## Locked scope

```text
IN:  exact / near / relation file rows (active Resolve filter + status unreviewed)
IN:  Server dry-run summary (full filter, no grid preload)
IN:  Background job + snapshot progress polling
IN:  Internal chunked SQLite mutations (single writer; no public 500 cap in bulk UX)
IN:  Keeper policy: largest size_bytes → newest modified_at_ns → stable file_id tie-break
IN:  Conflict/exclusion skip; cooperative cancel; partial failure + audit log

OUT: move preview auto-generation
OUT: file move / apply
OUT: finalize / integrity
OUT: full pipeline one-shot (auto-approve → preview → apply)
OUT: checkbox / explicit multi-select revival
```

Keeper policy, conflict exclusion, and preview-before-apply rules remain governed by [NOV-32 policy](../../adr/NOV-32-auto-keeper-policy.md) and [033 auto-keeper bulk approve policy](033-2026-06-05-auto-keeper-bulk-approve-policy.md).

## Keeper policy lock (contract)

For **exact**, **near**, and **relation** duplicate/review groups, the automatic keeper is selected by:

1. **Largest** `size_bytes` (desc)
2. **Newest** `modified_at_ns` (desc)
3. **Stable** `file_id` tie-breaker (asc)

All non-keeper **file** rows in eligible groups are approved for `move_duplicate`. Keeper rows are preserved (`approved` + `keep`). `conflict`, `excluded`, and manual-blocked rows are **not** mutated unless explicitly included by locked policy in [033](033-2026-06-05-auto-keeper-bulk-approve-policy.md).

Implementation must use canonical `pick_keeper_file_id` (or equivalent) — no alternate client-side keeper logic in the bulk job path.

Deferred follow-up issue:

> **Resolve pipeline CTA: auto-approve → move preview handoff**

## Problem

Today’s bulk approve path couples three separate pains:

| Pain | Current behavior |
|------|------------------|
| Partial summary | Confirm dialog uses `computeAutoSelectSummary` over **loaded grid rows** only; 7k libraries load first page → inaccurate counts |
| Repeated clicks / chunks | Client loops `bulkMutationChunkCursors` with multiple `summarizeAutoSelectKeepers` + `updateReviewDecisions` bridge calls |
| Public 500 cap | `MAX_REVIEW_MUTATIONS` limits each bridge mutation; user must re-run for large filters |
| Post-approve reload | `loadAllFiltered()` after approve forces sequential page fetches through the bridge |

The UI timeout/degraded-loading work in [034](034-2026-06-05-infra-large-library-loading-stability-design.md) stabilizes **reads**; this spec stabilizes **bulk approve writes**.

## Goals

| Goal | Pass condition |
|------|----------------|
| Server-authoritative summary | Confirm dialog counts reflect full current filter, not loaded rows |
| One-shot UX | User confirms once; server runs to completion or cancel |
| No grid preload required | Bulk approve does not call `loadAllFiltered` |
| Safe persistence | SQLite writes are single-writer, chunked transactions |
| Observable progress | UI polls snapshot job block; no long-running bridge call |
| Policy preserved | NOV-32 keeper tie-break, conflict skip, preview gate unchanged |

## Non-goals

- Parallel SQLite writers across threads
- Removing `MAX_REVIEW_MUTATIONS` from direct `update_review_decisions` safety rail
- Auto-running move preview or apply after job completion
- Checkbox / explicit multi-select revival

## Recommended architecture (Approach A)

Session-embedded job with snapshot polling — mirrors existing `LibrarySession` scan/post-scan worker patterns.

Rejected alternatives:

| Approach | Verdict |
|----------|---------|
| Dedicated `get_job_status(job_id)` + job registry | YAGNI — only one bulk job at a time |
| Client chunk loop + longer bridge timeout | Does not fix partial summary or repeated UX |

## Bridge API

### New methods

| Method | Sync | Purpose |
|--------|------|---------|
| `summarize_resolve_auto_approve(query)` | yes | Full-filter preflight for confirm dialog |
| `start_resolve_auto_approve_job(query)` | yes | Accept job, spawn worker, return immediately |
| `cancel_resolve_auto_approve_job()` | yes | Cooperative cancel between internal chunks |

### Snapshot extension

Add `resolveAutoApproveJob` to `get_snapshot()` payload (validated in `validate_app_snapshot`).

```text
resolveAutoApproveJob: {
  status: "idle" | "running" | "complete" | "error" | "cancelled"
  phase: "idle" | "set_keeper" | "approve" | "persist"
  processedRows: int
  totalRows: int
  keeperCount: int
  moveCandidateCount: int
  label: string          # e.g. "처리 중…"
  error: string | null
  startedAt: string | null   # ISO-8601
  finishedAt: string | null
}
```

When `status === "idle"` and no job has run this session, counters may be zero and timestamps null.

### Method contracts

#### `summarize_resolve_auto_approve(query)`

- Input: same `ReviewRowsQuery` shape as Resolve grid (`viewMode`, `filters`, `sort`; ignore client `cursor`).
- Server merges `filters.status = ["unreviewed"]`.
- Scans `_review_rows_cache` via `query_review_page` streaming until exhausted.
- Includes only `rowKind === "file"` rows; skips `status === "conflict"`.
- **No 500 cap** on target rows.
- Computes per-group keeper via `pick_keeper_file_id` and `files_by_id` (NOV-32 tie-break).
- Returns:

```text
{
  unreviewedCount: int
  keeperCount: int
  moveCandidateCount: int
  exactCount: int
  nearCount: int
  relationCount: int
  samples?: { keepers, moveCandidates, exact, near, relation }  # max 5 names each
}
```

- Does **not** mutate state.
- Expected to complete synchronously; may take seconds on 7k+ filters but must not spawn a worker.

#### `start_resolve_auto_approve_job(query)`

- Rejects with `JOB_ALREADY_RUNNING` when a job is active.
- Rejects with `NO_UNREVIEWED_TARGETS` when summarize would return zero file rows.
- Captures immutable job plan from the same selection logic as summarize (keeper row ids + approve targets).
- Spawns background thread on `LibrarySession`.
- Returns `{ accepted: true }` within a short bridge window (< 2s).

#### `cancel_resolve_auto_approve_job()`

- Sets cooperative cancel flag read between chunks.
- Completed chunks remain committed.
- Final status: `cancelled`.

### Deprecated for this UX path (retain for tests / migration)

- Client `computeAutoSelectSummary` as confirm source
- Client `bulkMutationChunkCursors` loop in `runAutoSelectKeepersAndApprove`
- Client-side `summarizeAutoSelectKeepers` + `updateReviewDecisions` pairing for auto-select button

Existing `summarize_auto_select_keepers` and `update_review_decisions` remain for direct bridge callers until a later cleanup PR.

## Server worker design

### Flow

```text
UI click [미검토 자동 선정·승인]
  → summarize_resolve_auto_approve(currentQuery)     # bridge call 1
  → confirm dialog (server counts)
  → start_resolve_auto_approve_job(currentQuery)     # bridge call 2
  → poll get_snapshot().resolveAutoApproveJob
  → on complete: refresh snapshot + reload grid first page only
```

### Worker phases

```text
1. set_keeper
   For each planned keeper row id (internal chunks of JOB_MUTATION_CHUNK):
     apply setKeeper via existing review decision merge paths

2. approve
   For each remaining unreviewed file row in plan (chunked):
     apply approve with keeper vs non-keeper proposedAction semantics

3. persist
   Each chunk: one SQLite transaction (single writer)
   Update processedRows / totalRows after each committed chunk
```

Constants:

```text
JOB_MUTATION_CHUNK = 200   # internal server chunk size; mirrors SELECTION_RESOLVE_ROW_CAP
MAX_REVIEW_MUTATIONS = 500 # unchanged for direct update_review_decisions calls only
```

### Threading and locking

```text
summarize: short LibrarySession._lock read of review cache + files_by_id

worker:
  build immutable plan under short lock
  for each chunk:
    compute row mutations outside lock where safe
    acquire short lock to apply in-memory session state
    release lock
    persist to SQLite (single writer, no lock held across I/O)
    update job progress under lock
    if cancel requested: stop after chunk commit
  rebuild review projection + bump library_revision on completion
```

**Do not** issue parallel SQLite writes from multiple threads.

Optional future optimization (out of scope): parallel CPU-only keeper grouping before single-writer persist.

### Concurrency

- At most **one** active resolve auto-approve job per `LibrarySession`.
- Starting scan or another destructive session operation while job runs: document behavior — job cancel or reject `start_scan`; pick **reject start_scan while job running** for safety.

### Error handling

| Case | Behavior |
|------|----------|
| 0 unreviewed targets | `start_*` rejected; button disabled after summarize |
| Job already running | `start_*` rejected; UI shows progress |
| Cancel mid-job | status `cancelled`; partial commits kept |
| SQLite busy | retry with existing `busy_timeout`; fail job after bounded retries |
| Unexpected exception | status `error`; `error` string in snapshot; partial commits kept |

## UI changes

### Confirm dialog

- Fetch summary from `summarize_resolve_auto_approve` on button click.
- Remove `partialLoad` and `capped` messaging for this flow.
- Keep NOV-32 keeper tie-break copy and sample names.

### Batch action bar

- While `resolveAutoApproveJob.status === "running"`: disable bulk actions; show inline progress (`processedRows / totalRows`).
- Optional cancel control if low effort; otherwise defer.

### After completion

- `refreshSnapshot()`
- Reload **first page** of current query only (`queryReviewRows` with `cursor: null`).
- Do **not** call `loadAllFiltered()`.

### Polling

- Reuse existing snapshot poll interval (~500ms–1s) while job `running`.
- No long `callBridge` timeout on job execution — only summarize/start/cancel are synchronous bridge calls.

## Policy alignment (NOV-32)

Unchanged from locked policy — server job is the **delivery mechanism**, not a policy change:

| Rule | Job behavior |
|------|----------------|
| Scope | Active Resolve filter + `status: unreviewed` |
| Row types | exact, near, relation file rows |
| Keeper | `pick_keeper_file_id` — size desc → `modified_at_ns` desc → `file_id` asc |
| Keeper approve | `approved` + `keep` |
| Non-keeper approve | `approved` + `move_duplicate` |
| Conflict / excluded | skipped — no mutation |
| Public 500 cap | **not** exposed in bulk UX; internal chunks only |
| Preview | user must still run move preview separately |
| Audit | job start/complete/cancel/error recorded in session audit log |

## Testing

| Layer | Cases |
|-------|-------|
| Python unit | summarize >500 rows; worker chunk commits; cancel mid-run preserves partial state |
| Bridge contract | validate new methods + `resolveAutoApproveJob` snapshot field |
| Web unit | confirm uses server summary; no client chunk loop; progress from snapshot |
| Integration | 7k fixture: one confirm → job complete → counts updated |
| E2E | `batch-auto-select-keepers` without `batch-loading-all` |

## Code touch map

| Area | Path |
|------|------|
| Spec | `docs/superpowers/specs/035-2026-06-05-resolve-bulk-auto-approve-job-design.md` |
| Plan | `docs/superpowers/plans/035-2026-06-06-resolve-bulk-auto-approve-job.md` |
| Job logic | `src/application/resolve_auto_approve_job.py` (new) |
| Session wiring | `src/application/library_session.py` |
| Bridge | `src/app/bridge_api.py`, `src/app/bridge_parity.py` |
| Contract | `src/app/bridge_contract.py`, `web/src/contracts/snapshotContract.ts` |
| Types | `web/src/types/snapshot.ts`, `web/src/bridge/NovelGuardBridge.ts` |
| UI | `web/src/features/work/ResolveAndOrganizeWorkspace.tsx`, `AutoSelectKeepersConfirmDialog.tsx` |
| Tests | `tests/test_bridge_contract.py`, `web/e2e/smoke.spec.ts` |

## Acceptance criteria

| # | Criterion |
|---|-----------|
| 1 | Confirm dialog shows full-filter unreviewed count without grid preload on 7k library |
| 2 | Single confirm runs server job to completion for >500 unreviewed rows |
| 3 | UI exposes no public 500-cap messaging for this button |
| 4 | `loadAllFiltered` is not invoked by bulk auto-select flow |
| 5 | Snapshot progress updates during job; no user-facing bridge timeout on job execution |
| 6 | Cancelled/error jobs leave prior chunk commits intact |
| 7 | Move preview remains manual separate step |

## Out of scope

- Auto preview after job complete
- Apply / finalize automation
- Library-wide shortcut bypassing active filter
- Multi-job registry or `job_id` in v1
