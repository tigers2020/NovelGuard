# Resolve Bulk Auto-Approve Job — Implementation Plan

> **Status:** `contract-review` / **not executed on `main`**
> **Do not implement** until spec 035 contract PR merges and plan is approved.
> **WIP reference:** `wip/mixed-035-036-salvage` — spec only; no 035 code to restore.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans.

**Goal:** Replace client chunked bulk approve with a server-authoritative background job: full-filter dry-run summary, progress polling, internal chunked mutations — without exposing `MAX_REVIEW_MUTATIONS = 500` in the bulk UX.

**Architecture:** Session-embedded worker on `LibrarySession` (mirrors post-scan worker). New bridge methods `summarize_resolve_auto_approve`, `start_resolve_auto_approve_job`, `cancel_resolve_auto_approve_job`. Snapshot field `resolveAutoApproveJob` for polling.

**Spec:** [035-2026-06-05-resolve-bulk-auto-approve-job-design.md](../specs/035-2026-06-05-resolve-bulk-auto-approve-job-design.md) (contract-review)

**Branch:** `feature/resolve-bulk-auto-approve-job` (after contract merge)

**Test policy:** Extend existing `tests/test_bridge_contract.py`, `tests/test_keeper_selection.py`, `web/src/bridge/bridgeParity.test.ts`, `web/e2e/smoke.spec.ts`. No new test files without `TEST_ALLOWED`.

---

## Vertical slices

| Slice | Scope | Mode |
|-------|-------|------|
| **1** | Server dry-run summary + keeper policy tests | AFK |
| **2** | Background job model + progress polling API | AFK |
| **3** | Bulk approve execution with internal chunked mutations | AFK |
| **4** | Resolve UI button / status / progress integration | AFK/HITL |

Implement in order. Each slice should merge behind feature flag or idle snapshot state until slice 4 wires UI.

---

## Slice 1 — Dry-run summary + keeper policy

**Deliverables**

- `summarize_resolve_auto_approve(query)` bridge method
- Full-filter scan of unreviewed file rows (exact / near / relation)
- Counts: `unreviewedCount`, `keeperCount`, `moveCandidateCount`, per-type breakdown
- No mutation; no public 500 cap on summary scan
- Keeper via `pick_keeper_file_id` — size desc → `modified_at_ns` desc → `file_id` asc

**Files (expected)**

| File | Action |
|------|--------|
| `src/application/resolve_auto_approve_job.py` | Create — summarize + plan builder |
| `src/app/bridge_api.py` | Modify — expose summarize |
| `src/app/bridge_contract.py` | Modify — validate summarize payload |
| `tests/test_bridge_contract.py` | Modify — summarize fixtures >500 rows |
| `tests/test_keeper_selection.py` | Modify — near/relation group fixtures |

**Gate**

```bash
pytest tests/test_keeper_selection.py tests/test_bridge_contract.py -k "auto_approve or summarize_resolve" -v
```

---

## Slice 2 — Job model + polling API

**Deliverables**

- `resolveAutoApproveJob` block on `get_snapshot()`
- `start_resolve_auto_approve_job(query)` — accept plan, spawn worker thread, return immediately
- `cancel_resolve_auto_approve_job()` — cooperative cancel between chunks
- Reject `JOB_ALREADY_RUNNING`, `NO_UNREVIEWED_TARGETS`
- Audit log entries: job started / completed / cancelled / error

**Files (expected)**

| File | Action |
|------|--------|
| `src/application/library_session.py` | Modify — job state + worker hook |
| `src/application/resolve_auto_approve_job.py` | Modify — job runner skeleton |
| `src/app/bridge_contract.py` | Modify — snapshot field |
| `web/src/contracts/snapshotContract.ts` | Modify — TS validator |
| `web/src/types/snapshot.ts` | Modify — types |
| `web/src/bridge/mockBridge.ts` | Modify — mock job block |

**Gate**

```bash
pytest tests/test_bridge_contract.py -k "resolve_auto_approve or snapshot" -v
cd web && npm run test:contracts
```

---

## Slice 3 — Chunked execution

**Deliverables**

- Worker phases: `set_keeper` → `approve` → `persist`
- `JOB_MUTATION_CHUNK = 200` internal chunks; single-writer SQLite per chunk
- Progress: `processedRows` / `totalRows` updated after each committed chunk
- Cancel mid-job: status `cancelled`; prior chunks kept
- Error: status `error`; partial commits kept; bounded SQLite busy retry
- Rebuild review projection + `library_revision` bump on completion
- Reject `start_scan` while job running

**Files (expected)**

| File | Action |
|------|--------|
| `src/application/resolve_auto_approve_job.py` | Modify — full worker |
| `src/application/library_session.py` | Modify — lock discipline |
| `tests/test_bridge_contract.py` | Modify — cancel + partial failure |

**Gate**

```bash
pytest tests/test_bridge_contract.py -k resolve_auto_approve -v
```

---

## Slice 4 — Resolve UI integration

**Deliverables**

- `미검토 자동 선정·승인` uses server summarize for confirm dialog (no `loadAllFiltered`)
- Remove client `bulkMutationChunkCursors` loop for this button path
- Inline progress from snapshot while `status === "running"`
- On complete: `refreshSnapshot()` + reload first page only
- Optional cancel control (defer if not low effort)
- E2E: `batch-auto-select-keepers` without `batch-loading-all`

**Files (expected)**

| File | Action |
|------|--------|
| `web/src/features/work/ResolveAndOrganizeWorkspace.tsx` | Modify |
| `web/src/features/work/resolve/AutoSelectKeepersConfirmDialog.tsx` | Modify |
| `web/src/bridge/bridgeParity.test.ts` | Modify |
| `web/e2e/smoke.spec.ts` | Modify |

**Gate**

```bash
cd web && npm run test:contracts
cd web && npm run test:e2e -- smoke.spec.ts
python scripts/verify_phase_completion.py
```

---

## Out of scope (all slices)

- Auto move preview after job complete
- Apply / finalize automation
- Multi-job registry / `job_id` in v1
- Parallel SQLite writers

---

## Implementation status

**Not started** — awaiting contract PR merge + plan approval.
