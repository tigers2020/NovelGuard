---
title: Partial Success Recovery and Undo Plan
status: proposed
date: 2026-06-06
risk: design-only
authors: P2/P3 safety design gate
parent_spec: docs/architecture/main-ux-contract.md
related_specs:
  - docs/superpowers/specs/003-2026-06-01-real-apply-use-cases-design.md
  - docs/superpowers/specs/010-2026-06-02-quality-repair-execution-design.md
  - docs/superpowers/specs/011-2026-06-02-finalize-cleanup-pipeline-design.md
  - docs/superpowers/specs/027-2026-06-03-infra-quality-finalize-cleanup-debt-design.md
supersedes_policy: none
implementation: forbidden in this PR
---

# Partial success recovery and undo plan

## Status

**Proposed** (2026-06-06) — **docs-only safety contract**. No production code, UI, or pipeline behavior change in this PR.

**Success criterion:** Later implementation PRs can cite this spec as the authoritative contract for checkpoints, undo plans, recovery policy, UI surfaces, and tests.

---

## Scope sentence

Define how NovelGuard records **reversible filesystem mutations**, materializes **undo plans**, classifies **partial success**, and exposes **user-visible recovery** across move apply, UTF-8 repair, and finalize cleanup — without implementing the executor.

---

## Problem statement

Destructive or semi-destructive operations can **partially succeed** today:

| Operation | Partial-success signal today | Undo today |
|-----------|------------------------------|------------|
| Duplicate move (`applyResolvedActions`) | `APPLY_FAILED` + `details.partialSuccess`, `succeededCount`, `failedRowId` | None — audit only |
| UTF-8 repair (`applyQualityRepair`) | `REPAIR_FAILED` + same shape + `failedIssueId` | Per-file backup exists; no orchestrated restore |
| Finalize empty-dir cleanup | Report lists `removedEmptyDirs`; no per-dir checkpoint | None — removed dirs are not restorable |

Existing guards (preview token, revision, drift checks, repair backup, finalize allowlist) **reduce** risk but do not define:

- A unified **operation checkpoint** model
- A durable **undo plan** format and executor contract
- **When** to stop, auto-rollback, or require manual intervention
- **Recovery UX** beyond a one-line error string
- **Test contract** for partial-failure scenarios

---

## Current baseline (code truth)

| Item | Today |
|------|--------|
| Move apply | Sequential ops in `ApplyResolvedActionsUseCase`; ≥1 success → revision bump; failure clears pending preview |
| Repair apply | Sequential ops; backup at `SAVE/repair_backup/<sessionId>/<fileId>/` before in-place rewrite |
| Audit | Append-only `apply-audit.jsonl` per library under `state/libraries/<libraryId>/` |
| Partial UI (move) | `ApplySubflowDialog` shows Korean message + suggests audit log; refreshes snapshot |
| Partial UI (repair) | Error path only; no dedicated recovery surface |
| Finalize cleanup | `duplicate/` and `organized/` allowlist only; batch `rmdir` on preview list |
| Auto-rollback | **Explicitly absent** in specs 003 and 010 (v1) |
| Work orchestration | Scan pipeline in `LibrarySession`; apply/repair/finalize are **subflow dialogs** (`ApplySubflowDialog`, `RepairSubflowDialog`, `FinalizeSubflowDialog`) plus `PreflightPipelineDialog` for full-run preflight — not a single `PipelineRunConfirmSheet` component |

This design **does not** change the above behavior until dedicated implementation PRs land.

---

## Architectural placement

```text
UI (subflow dialogs + recovery banner)
  ↓ bridge methods (future: getRecoveryState, executeUndoPlan, …)
Application (checkpoint writer, undo planner, recovery classifier)
  ↓ ports
Infrastructure (atomic FS moves, backup restore, JSONL/SQLite persistence)
```

**Invariant (unchanged):** UI must not orchestrate filesystem recovery. Checkpoints and undo execution live in `application` / `app` use cases, same boundary as move/repair apply ([main-ux-contract.md](../../architecture/main-ux-contract.md)).

**Audit vs checkpoint:**

| Artifact | Purpose | Mutability |
|----------|---------|------------|
| `apply-audit.jsonl` | Human traceability, finalize tail input | Append-only; never rewritten |
| Undo plan + checkpoints | Machine-actionable recovery | Immutable once `status: sealed`; new plan version on retry |

Audit events **may** reference `operationId` / `undoPlanId` but audit rows are not sufficient alone to execute undo.

---

## 1. Operation taxonomy

### 1.1 Operation kinds

| `operationType` | Description | Reversibility class | Backup required |
|-----------------|-------------|---------------------|-----------------|
| `move_duplicate` | Library-confined file move (source → dest under `SAVE/duplicate/…`) | **Reversible move** | Optional metadata only (dest path is sufficient if source vacant) |
| `utf8_convert` | In-place encoding rewrite | **Reversible text repair** | **Required** — `original.bin` + `metadata.json` (existing layout) |
| `finalize_empty_dir_remove` | `rmdir` on allowlisted empty directory | **Conditionally reversible** | **No** filesystem backup; checkpoint records path + parent existence only |
| `finalize_placeholder` | Future non-empty cleanup (out of scope) | TBD per future spec | TBD |

### 1.2 Reversibility classes

| Class | Undo mechanism | Failure modes |
|-------|----------------|---------------|
| **Reversible move** | Move dest → original source if source vacant and metadata matches | Source reoccupied, dest missing, cross-volume edge cases |
| **Reversible text repair** | Restore `original.bin` over target via atomic replace | Backup missing/corrupt, file edited after repair |
| **Conditionally reversible cleanup** | Cannot restore directory contents; undo = recreate empty dir if parent exists and path still allowlisted | Parent removed, path now non-empty, path outside allowlist |
| **Irreversible cleanup** | No auto-undo; manual + `manualRequired` flag | Hard delete, non-empty dir removal (future) |

### 1.3 Per-item terminal states

| `itemStatus` | Meaning |
|--------------|---------|
| `no_op` | Planned but intentionally skipped (policy, already applied) |
| `skipped` | Skipped at apply time (drift, conflict) — filesystem unchanged |
| `failed` | Attempted; filesystem unchanged for this item |
| `applied` | Successfully committed |
| `partially_applied` | **Batch-level only** — run stopped mid-batch with mixed `applied` + `failed`/`skipped` |
| `recovered` | Previously `applied`; successfully undone by undo executor |
| `recovery_failed` | Undo attempted; item remains inconsistent — needs manual |
| `unrecoverable` | Classifier decided undo unsafe or impossible |

### 1.4 Run-level statuses

| `runStatus` | Condition |
|-------------|-----------|
| `completed` | All executable items `applied` or `skipped` |
| `failed` | Zero items `applied` |
| `partially_applied` | ≥1 `applied` and run aborted before completing plan |
| `undo_completed` | Undo plan executed; all targeted items `recovered` or acceptable `skipped` |
| `undo_partial` | Undo stopped with mixed outcomes |

---

## 2. Checkpoint model

### 2.1 Purpose

Each **successful mutation** (or attempted cleanup removal) emits one **checkpoint** before the next item in the same batch. Checkpoints are the source of truth for undo ordering and drift checks.

### 2.2 Checkpoint record (JSON object)

```json
{
  "schemaVersion": 1,
  "operationId": "uuid-v4",
  "runId": "uuid-v4",
  "jobId": "uuid-v4-or-null",
  "batchKind": "move_apply | repair_apply | finalize_cleanup",
  "operationType": "move_duplicate | utf8_convert | finalize_empty_dir_remove",
  "libraryId": "sha256-of-normalized-root",
  "libraryRevisionBefore": 42,
  "libraryRevisionAfter": 43,
  "previewToken": "move-preview-token-or-null",
  "repairPreviewToken": "repair-token-or-null",
  "finalizeReportId": "report-id-or-null",
  "sourcePath": "relative/or/null",
  "destinationPath": "relative/or/null",
  "backupPath": "SAVE/repair_backup/.../original.bin-or-null",
  "before": {
    "exists": true,
    "size": 12345,
    "contentHash": "sha256-hex-or-null",
    "mtimeNs": 123456789,
    "encoding": "cp949-or-null"
  },
  "after": {
    "exists": true,
    "size": 12000,
    "contentHash": "sha256-hex-or-null",
    "mtimeNs": 987654321,
    "encoding": "utf-8-or-null"
  },
  "rowId": "file:group:file-or-null",
  "issueId": "quality:...-or-null",
  "fileId": "stable-file-id-or-null",
  "status": "applied",
  "error": null,
  "createdAt": "2026-06-06T12:00:00.000Z",
  "sequence": 3
}
```

### 2.3 Field rules

| Field | Rule |
|-------|------|
| `operationId` | Unique per committed mutation; stable across undo retries |
| `runId` | One apply/finalize invocation; ties checkpoints in execution order |
| `jobId` | Set for async finalize job runs; null for synchronous apply |
| `sequence` | 1-based order within `runId`; undo executes **descending** sequence |
| `previewToken` / `repairPreviewToken` | Copy from frozen plan; used for stale linkage, not re-apply |
| `before` / `after` | Captured best-effort immediately around mutation; repair must include `encoding` in `before` |
| `backupPath` | Required for `utf8_convert`; null for moves if policy uses dest-only undo |
| `status` | `applied` at write time; updated to `recovered` / `recovery_failed` by undo executor |

### 2.4 Storage

| Store | Location | Format |
|-------|----------|--------|
| Checkpoint log | `{library_state_dir}/recovery-checkpoints.jsonl` | Append-only JSONL, one checkpoint per line |
| Run index (optional) | `{library_state_dir}/recovery-runs.json` | Map `runId` → summary; implementation may use SQLite later |

Checkpoints **must not** live inside the scanned library tree (same rule as audit log).

### 2.5 Write timing

| Operation | When to append checkpoint |
|-----------|---------------------------|
| Move | Immediately after successful `move_file`; before next op |
| Repair | After atomic replace succeeds; `backupPath` must already exist |
| Finalize cleanup | After each successful `rmdir`; before next dir |

If process crashes **after** FS mutation but **before** checkpoint append, recovery treats the item as **untracked manual** — audit tail may hint but is not authoritative.

---

## 3. Undo plan contract

### 3.1 Artifact shape

Undo plan is a **sealed document** produced when a run ends `partially_applied` or when user requests undo after `completed`.

```json
{
  "schemaVersion": 1,
  "undoPlanId": "uuid-v4",
  "runId": "uuid-v4",
  "libraryId": "sha256",
  "createdAt": "2026-06-06T12:00:01.000Z",
  "sealedAt": "2026-06-06T12:00:01.100Z",
  "status": "pending | executing | completed | partial | expired | superseded",
  "sourceBatchKind": "move_apply",
  "sourcePreviewToken": "token",
  "libraryRevisionAtSeal": 43,
  "summary": {
    "appliedCount": 5,
    "skippedCount": 0,
    "failedCount": 1,
    "recoverableCount": 5,
    "manualCount": 0,
    "unrecoverableCount": 0
  },
  "items": [
    {
      "operationId": "uuid",
      "sequence": 5,
      "operationType": "move_duplicate",
      "undoAction": "move_back",
      "fromPath": "SAVE/duplicate/...",
      "toPath": "original/relative.txt",
      "backupPath": null,
      "recoverability": "recoverable",
      "manualRequired": false,
      "driftPolicy": "strict",
      "collisionPolicy": "block",
      "checkpointRef": { "beforeHash": "...", "afterHash": "..." }
    }
  ],
  "idempotencyKey": "sha256(runId + sealed checkpoint ids ordered desc)"
}
```

**JSONL variant:** For long plans, `items` may spill to `undo-plan-{undoPlanId}.jsonl` with the header JSON holding counts + path reference. Executor must support both; v1 may use single JSON file capped at 10 MB.

### 3.2 Storage location

```text
state/libraries/<libraryId>/
  recovery-checkpoints.jsonl
  undo-plans/
    <undoPlanId>.json
```

### 3.3 Retention policy

| Artifact | Retention |
|----------|-----------|
| Checkpoints | Until undo plan `completed` or `expired`, plus **30 days** after seal |
| Undo plan | Same as checkpoints |
| Repair backups | Until undo `completed` **or** 30 days after repair apply — **whichever is longer** if plan pending |
| Sealed plan after successful undo | Mark `superseded`; keep read-only 90 days for support |

Rotation implementation is out of scope for first executor PR; policy must be documented in settings/logs UX.

### 3.4 Idempotency rules

| Rule | Behavior |
|------|----------|
| Same `idempotencyKey` + `status: completed` | Second `executeUndoPlan` → no-op success |
| `status: executing` + lease timeout | Resume or fail with `UNDO_IN_PROGRESS` |
| Item already `recovered` | Skip item; count as success |
| Mixed re-entry | Executor re-reads plan from disk; never trusts UI-only state |

### 3.5 Stale / source drift checks (per item)

| `operationType` | Pre-undo checks |
|-----------------|-----------------|
| `move_duplicate` | Dest file exists; hash/size matches `after`; source path absent or matches empty expectation |
| `utf8_convert` | Target exists; `after` hash matches OR backup metadata matches; backup file readable |
| `finalize_empty_dir_remove` | Path does not exist; parent exists; still under allowlist |

Failure → item `recovery_failed` with `driftReason` (`dest_missing`, `dest_changed`, `source_occupied`, `backup_missing`, `parent_missing`, `not_allowlisted`).

### 3.6 Destination collision policy

| `collisionPolicy` | When undo would overwrite existing file |
|-------------------|----------------------------------------|
| `block` (default) | Abort item; run continues only if plan says `continue_on_error` |
| `manual` | Skip auto; set `manualRequired: true` |
| `quarantine` (future) | Move occupant to `SAVE/undo_collision/` — **not v1** |

### 3.7 Manual intervention flags

| Flag | Meaning |
|------|---------|
| `manualRequired: true` | UI shows manual steps; executor skips item |
| `manualReason` | Enum: `source_occupied`, `backup_missing`, `collision`, `partial_cleanup`, `cross_volume` |
| `supportHints` | Optional string list for logs UI |

---

## 4. Partial success recovery policy

### 4.1 When to stop (apply phase)

| Situation | Policy |
|-----------|--------|
| Per-item drift before mutation | Skip item (`skipped`); continue **only** if plan mode is `best_effort` (move/repair default: **stop remaining**) |
| FS error on item N | **Stop** items N+1..end; seal undo plan for 1..N-1 successes |
| Index refresh failure after move | Treat as `partially_applied`; seal undo plan; surface `refreshError` (existing behavior + plan) |
| User cancel mid-batch | Not supported for synchronous apply v1; async jobs use cancel between items (future) |

Aligns with [003](../specs/003-2026-06-01-real-apply-use-cases-design.md) stop-remaining rule; adds **mandatory** undo plan seal on partial.

### 4.2 When to auto-rollback

| Condition | Auto-rollback |
|-----------|---------------|
| Preview validation failure before any mutation | N/A — nothing to roll back |
| First item fails | No |
| Partial batch with ≥1 success | **No auto-rollback in v1** — user confirms undo |
| Repair low-confidence encoding | No — user already confirmed in subflow |
| Finalize cleanup mid-list crash | **No** — classify removed dirs as `recoverable` (recreate empty) or `manual` |

**Rationale:** Auto-rollback without user confirm risks secondary data loss (occupied source paths, user edits after partial apply). Future **opt-in** `autoUndoOnPartial` setting may be added only with explicit spec amendment.

### 4.3 When not to auto-rollback

- Any `source_occupied` on move-back
- `backup_missing` for repair
- `dest_changed` (file edited after apply)
- Items marked `unrecoverable`
- Library revision advanced by unrelated scan/apply after seal (plan goes `stale` — undo requires re-validate all items)

### 4.4 Safe resume after partial success

| Step | Action |
|------|--------|
| 1 | Seal checkpoint log + undo plan with `status: pending` |
| 2 | Clear pending preview tokens (existing) |
| 3 | Bump revision if ≥1 success (existing) |
| 4 | Set `work.recovery.activeRunId` in snapshot (future field) |
| 5 | Block new apply/repair previews that overlap affected paths until recovery cleared or dismissed |
| 6 | User chooses: **Undo**, **Dismiss** (accept partial), or **Manual** (open logs) |

**No double-move:** New move preview must exclude files with open recovery items unless undo plan `superseded` or `completed`.

**No double-restore:** Undo executor sets per-`operationId` lease; second invoke skips `recovered` items.

### 4.5 Recoverable vs non-recoverable classification

| Outcome | Criteria |
|---------|----------|
| **Recoverable** | All pre-undo checks pass; collision policy not triggered |
| **Manual** | `collisionPolicy: manual` failures; cross-volume move-back |
| **Unrecoverable** | Backup missing and bytes mismatch; path escapes allowlist; hard delete (future) |

Classifier runs at **plan seal** time (static) and **undo execution** time (dynamic re-check).

### 4.6 Finalize cleanup specifics

| Case | Classification |
|------|----------------|
| Dir removed, parent exists | `recoverable` via `mkdir` |
| Parent also removed | `manual` |
| Process crash mid-`remove_empty_dirs` | Seal plan with dirs removed so far; do not delete outside allowlist on resume |
| Cancel between runner steps before cleanup | No checkpoint writes |

Allowlist remains `duplicate`, `organized` only ([011](../specs/011-2026-06-02-finalize-cleanup-pipeline-design.md) G5).

---

## 5. UI contract

### 5.1 Surfaces (maps to current IA)

| Surface | Responsibility |
|---------|----------------|
| **Recovery banner** (new, global in Work shell) | Persistent when `work.recovery.hasActivePlan`; shows counts + primary CTA |
| **`ApplySubflowDialog`** | On `partialSuccess`, link to recovery detail instead of audit-only message |
| **`RepairSubflowDialog`** | Same pattern for `REPAIR_FAILED` + partial |
| **`FinalizeSubflowDialog`** | Post-run if cleanup partial / recovery pending |
| **`PreflightPipelineDialog`** | Unchanged; may add warning if recovery plan active |
| **Logs route** | Filter by `runId` / `undoPlanId`; link from banner |

No new top-level WorkMode tab. Recovery is overlay + banner per [main-ux-contract.md](../../architecture/main-ux-contract.md).

### 5.2 Recovery banner content

| Element | Requirement |
|---------|-------------|
| Headline | Korean — e.g. "일부 작업만 적용됨" |
| Counts | `applied`, `skipped`, `failed` from sealed plan |
| Split chips | `recoverable` / `manual` / `unrecoverable` |
| Primary CTA | "되돌리기 미리보기" → confirm sheet |
| Secondary | "로그 보기", "부분 적용 유지" (dismiss) |
| `data-testid` | `recovery-banner`, `recovery-undo-cta`, `recovery-dismiss` |

### 5.3 Undo confirmation sheet

| Requirement | Detail |
|-------------|--------|
| Explicit confirm | Separate step from apply confirm; destructive styling |
| Preview list | Per item: path, action (`move_back` / `restore_backup` / `recreate_dir`), recoverability chip |
| Blockers | Disable confirm if `unrecoverableCount > 0` and policy `strict` |
| Stale plan | Show `STALE_UNDO_PLAN` banner; force re-preview |
| Result | Success → toast + clear banner; partial → stay on banner with updated counts |

### 5.4 Bridge / snapshot extensions (future)

```typescript
work: {
  recovery: {
    hasActivePlan: boolean;
    undoPlanId: string | null;
    runId: string | null;
    batchKind: "move_apply" | "repair_apply" | "finalize_cleanup" | null;
    appliedCount: number;
    recoverableCount: number;
    manualCount: number;
    unrecoverableCount: number;
    sealedAt: string | null;
  };
}
```

Methods (names locked for planning; implement later):

- `getRecoveryState()`
- `previewUndoPlan({ undoPlanId })`
- `executeUndoPlan({ undoPlanId, confirmToken })`
- `dismissRecoveryPlan({ undoPlanId, acknowledgePartial: true })`

Errors: `UNDO_PLAN_NOT_FOUND`, `STALE_UNDO_PLAN`, `UNDO_IN_PROGRESS`, `UNDO_BLOCKED`, `LIBRARY_BUSY`.

### 5.5 Copy guidelines

- Korean primary strings; no English fallback in user-visible recovery copy
- Always mention that undo may fail if files changed externally
- Link to audit tail remains secondary to structured recovery view

---

## 6. Test contract

Implementation PRs must add tests (extend existing files per repo policy; no new test files without approval).

### 6.1 Move apply

| ID | Scenario | Assertion |
|----|----------|-----------|
| T-M1 | Failure after N successful moves | N checkpoints; undo plan `partially_applied`; revision bumped once |
| T-M2 | Undo after partial | Files restored; items `recovered`; idempotent second undo |
| T-M3 | Source reoccupied before undo | Item `recovery_failed`; `manualRequired`; no overwrite |
| T-M4 | Destination collision on undo | `block` policy stops item; plan `partial` |
| T-M5 | Source drift at apply | Item `skipped`; no checkpoint for that item |

### 6.2 Repair apply

| ID | Scenario | Assertion |
|----|----------|-----------|
| T-R1 | Failure after N repairs | N backups referenced; plan sealed |
| T-R2 | Undo restore | `original.bin` restored; quality re-analyzed |
| T-R3 | Backup missing | `unrecoverable`; executor no-op on item |
| T-R4 | File edited after repair | `dest_changed`; manual flag |

### 6.3 Finalize cleanup

| ID | Scenario | Assertion |
|----|----------|-----------|
| T-F1 | Interrupted cleanup | Only allowlisted paths in checkpoints; none outside `duplicate/` / `organized/` |
| T-F2 | Undo recreate dir | Empty dir recreated; parent missing → manual |
| T-F3 | Dir no longer empty | Skip recreate; manual |

### 6.4 Cross-cutting

| ID | Scenario | Assertion |
|----|----------|-----------|
| T-X1 | `executeUndoPlan` twice | Second call no-op `completed` |
| T-X2 | New move preview with active recovery | Blocked or excludes affected paths |
| T-X3 | Audit append-only | Undo does not rewrite audit; adds `undo_applied` events |
| T-X4 | Bridge contract | `getRecoveryState` shape validated in `bridge_contract` tests |

### 6.5 Web contract / E2E (when UI lands)

- Partial apply shows recovery banner with correct counts
- Undo confirm disabled when `unrecoverableCount > 0` (strict mode)
- Dismiss clears `hasActivePlan` without FS changes

---

## Locked decisions (implementation gates)

| ID | Decision |
|----|----------|
| **LOCK-R1** | Checkpoints append-only; undo never deletes checkpoint history |
| **LOCK-R2** | Undo order = reverse `sequence` within `runId` |
| **LOCK-R3** | No auto-rollback without future explicit setting + spec amendment |
| **LOCK-R4** | Move/repair partial batch stops remaining ops (unchanged) |
| **LOCK-R5** | Repair undo must use `backupPath`; move undo uses paths + hash checks |
| **LOCK-R6** | Finalize undo only recreates empty dirs — no content restoration |
| **LOCK-R7** | Recovery state blocks overlapping apply previews |
| **LOCK-R8** | Korean UI copy for recovery surfaces |
| **LOCK-R9** | Storage under `state/libraries/<libraryId>/` — never library scan root |
| **LOCK-R10** | Executor idempotent; safe under retry / crash |

---

## Out of scope (this program)

- Undo executor implementation
- Refactoring move/repair/finalize runners
- New React components (beyond spec contract)
- Scheduled retention jobs
- Performance optimization of checkpoint I/O
- Global command-stack undo in `GlobalActionToolbar`
- Hard delete / trash / quarantine collision handling
- Near/relation move apply

---

## Suggested implementation waves (informative)

| Wave | Deliverable | Depends on |
|------|-------------|------------|
| W1 | Checkpoint writer + seal plan on partial (move only) | This spec approved |
| W2 | Move undo executor + bridge + banner MVP | W1 |
| W3 | Repair checkpoints + restore | W1 |
| W4 | Finalize cleanup checkpoints + dir recreate undo | W1 |
| W5 | E2E + logs integration | W2–W4 |

Each wave requires its own plan under `docs/superpowers/plans/` referencing this spec.

---

## Verification (this PR)

```bash
# Docs-only diff
git diff --stat

# Optional link check if tooling exists
# No pytest / npm required for merge of design-only PR
```

---

## References

- [003 — Real apply use cases](../specs/003-2026-06-01-real-apply-use-cases-design.md) — partial failure, no v1 rollback
- [010 — Quality repair execution](../specs/010-2026-06-02-quality-repair-execution-design.md) — backup layout, LOCK-9
- [011 — Finalize pipeline](../specs/011-2026-06-02-finalize-cleanup-pipeline-design.md) — allowlist, runner steps
- [entry_points.md](../../entry_points.md) — audit path, apply behavior
