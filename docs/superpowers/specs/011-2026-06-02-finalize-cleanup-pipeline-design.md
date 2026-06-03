---
title: PR-23 Finalize / Cleanup Pipeline
status: approved
date: 2026-06-02
authors: PR-23 spec gate + codebase baseline
parent_spec: docs/superpowers/specs/010-2026-06-02-quality-repair-execution-design.md
related_specs:
  - docs/superpowers/specs/003-2026-06-01-real-apply-use-cases-design.md
  - docs/superpowers/specs/002-2026-06-01-novelguard-greenfield-library-session-design.md
roadmap: docs/superpowers/roadmap/001-2026-06-02-pr20-pr25-development-roadmap.md
pr_label: PR-23
plan: docs/superpowers/plans/017-2026-06-02-pr23-finalize-cleanup-pipeline.md
prerequisite_commit: "[pr22] quality repair execution"
---

# PR-23 — Finalize / Cleanup Pipeline

## Status

**Approved** (2026-06-02) — grill-me **G1–G6** + **B1–B4** locked below. Implementation per [plan 017](../plans/017-2026-06-02-pr23-finalize-cleanup-pipeline.md).

**Superseded (UX navigation only, 2026-06-03):** [Spec 021](./021-2026-06-02-feature-fullstack-shell-ia-reconciliation-design.md) **LOCK-33-7** removes WorkMode `finalize` (4th tab). Backend finalize runner, bridge methods, and `work.finalize` snapshot slice remain authoritative.

## Scope sentence

PR-23 wires **post-organize verification** into a product **Finalize** work mode: read-only summary of duplicate/quality state + move/repair audit tails, a **4-step background runner** (no blocking GUI event loop), optional **cleanup v1** (empty output folders only), JSON report under `SAVE/finalize/`, and UI for **「최종 검증 실행」** / **「완료 보고서 보기」**. It does **not** add new duplicate/repair mutations, packaging, or shell FileDock.

---

## Locked decisions (brainstorming — pre–grill-me)

| Item | Lock |
|------|------|
| Nature | **Limited mutation** — cleanup v1 may remove **empty directories** under library root only; no file delete |
| Work surface | New `WorkMode`: **`finalize`** (4th tab: 적용 · 검증) |
| Runner | **Background thread** on `LibrarySession` — same pattern as `start_scan` (no `QEventLoop` in web) |
| Progress | Reuse `snapshot.pipeline` fields during finalize run |
| Audit input | Read append-only JSONL (`apply-audit.jsonl`) — not used as detection input |
| Report output | `~/.novelguard/SAVE/finalize/<sessionId>/finalize_<timestamp>.json` |
| Re-verification | G4: cache recount + targeted quality reanalyze only; **no** full rescan |
| Tests | Extend `tests/test_bridge_contract.py` + `mockBridge` — no new test files without `TEST_ALLOWED` |

### Grill-me decision log

| # | Topic | Proposed lock | Status |
|---|--------|---------------|--------|
| G1 | Definition of **done** | Status mapping + discriminated `FinalizeResult` (report required for `blocked`/`complete`/`complete_with_warnings`; `cancelled`/`error` → `reportId`/`reportPath` null) | **Approved 2026-06-02** |
| G2 | **Blockers** (hard) | Five `FinalizeBlocker` codes; `UNRESOLVED_DUPLICATE_QUEUE` uses **exact-only** queue (`exact_unresolved_queue_count`) — raw `queueCount` forbidden; `LIBRARY_BUSY`/`NO_LIBRARY` are bridge errors only | **Approved 2026-06-02** |
| G3 | **Warnings** (soft) | Three codes; file-row counts; omit when count=0; no cleanup-empty warning; `FinalizeSummary.resolve.exactUnresolvedQueueCount` | **Approved 2026-06-02** |
| G4 | Re-verification | Resolve cache recount + targeted `reanalyze_quality_for_file_ids`; no scan/detection/hash recompute; **reverify** authoritative over precheck | **Approved 2026-06-02** |
| G5 | Cleanup v1 | Empty dirs only under `{library_root}/duplicate/**` and `organized/**`; checkbox = confirm; no `.novelguard` | **Approved 2026-06-02** |
| G6 | Completion lock | Milestone report only; no `libraryLocked`; re-run allowed; `libraryRevision` bump **only** if cleanup removed dirs | **Approved 2026-06-02** |

### Blocker resolution log

| # | Topic | Resolution | Status |
|---|--------|------------|--------|
| B1 | Blocker vs warning UX | UI disables CTA/checkbox when summary blockers; bridge allows `run_finalize_verification`; post-run table | **Approved 2026-06-02** |
| B2 | Pipeline steps | Fixed 4 steps: `precheck` → `reverify` → `cleanup_preview` → `report` | **Approved 2026-06-02** |
| B3 | Cancel | `cancel_finalize` sets flag; runner exits between steps; pipeline → idle | **Approved 2026-06-02** |
| B4 | Near/relation | Never block finalize on near/relation apply (unsupported); relation unreviewed = **warning** only (G3) | **Approved 2026-06-02** |

### G1 Approved — 2026-06-02

`FinalizeResult.status` mapping is locked as:

1. **`blocked`** — `blocker >= 1` after precheck or reverify; report **MUST** be written; `includeCleanup=true` ignored (cleanup skipped); `work.finalize.lastStatus = "blocked"`.
2. **`complete`** — `blocker == 0` and `warning == 0`; report **MUST** be written; `work.finalize.lastStatus = "complete"`.
3. **`complete_with_warnings`** — `blocker == 0` and `warning >= 1`; report **MUST** be written; `work.finalize.lastStatus = "complete_with_warnings"`.
4. **`cancelled`** — `cancel_finalize` observed between steps; **no** report in v1; pipeline → idle; `work.finalize.lastStatus = "idle"`.
5. **`error`** — runner exception or report IO failure; no report required if report write fails; `work.finalize.lastStatus = "error"`.

`LIBRARY_BUSY` is **not** `FinalizeResult.status = "error"`; it is rejected before runner start (bridge error).

`blocked` always writes a report (audit / retry / user explanation). Option B (no report on blocked) is **rejected**.

### G2 Approved — 2026-06-02

`FinalizeBlocker` hard conditions are locked as:

1. **`PENDING_MOVE_PREVIEW`** — `resolve.hasPendingApply == true` (duplicate/move preview not applied or cleared).
2. **`PENDING_REPAIR_PREVIEW`** — `session.hasPendingQualityRepair == true` (quality repair preview not applied or cleared).
3. **`SCAN_NOT_SUCCESS`** — `work.scan.state != "success"` (includes `empty`, `ready`, `running`, `error`, cancelled, or unknown).
4. **`UNRESOLVED_DUPLICATE_QUEUE`** — exact file rows only: `rowKind == "file"` AND `type == "exact"` AND `status in {"unreviewed", "conflict"}` AND count > 0. **Raw `snapshot.work.resolve.queueCount` MUST NOT** be used for this blocker.
5. **`QUALITY_ERROR_ISSUES`** — `encodingIssueCount + integrityIssueCount > 0`. `smallFileAnomalyCount` is excluded (G3 warning).

**Explicit non-blockers:** `small_file` anomalies; near duplicate rows; relation rows; unreviewed relation rows; near/relation-only conflicts; `LIBRARY_BUSY`; `NO_LIBRARY`.

`LIBRARY_BUSY` / `NO_LIBRARY` are `FinalizeErrorCode` values rejected at bridge call time — **not** entries in `FinalizeBlocker[]`.

**Implementation:** `exact_unresolved_queue_count(session)` in `application/finalize_blockers.py` (see plan 017).

### G3 Approved — 2026-06-02

`FinalizeWarning` soft conditions are locked as:

1. **`SMALL_FILE_ANOMALIES`** — emit when `smallFileAnomalyCount > 0`; `count = work.quality.smallFileAnomalyCount`; never includes encoding or integrity.
2. **`UNREVIEWED_RELATION`** — emit when unresolved relation **file** rows exist: `rowKind == "file"` AND `type == "relation"` AND `status in {"unreviewed", "conflict"}`; group/header rows excluded.
3. **`NEAR_GROUPS_PRESENT`** — emit when unresolved near **file** rows exist: `rowKind == "file"` AND `type == "near"` AND `status in {"unreviewed", "conflict"}`; group/header rows excluded.

**Warning emission rules:**

- If `count == 0`, omit the warning entry entirely.
- Do not duplicate blockers as warnings.
- Encoding/integrity → `QUALITY_ERROR_ISSUES` blocker only; `small_file` → `SMALL_FILE_ANOMALIES` warning only.
- Empty cleanup candidate count is **not** a `FinalizeWarning` (runner/UI info only).
- Near/relation `conflict` → warning only; exact `conflict` → blocker (G2).

**`FinalizeSummary.resolve` extension:**

```typescript
resolve: {
  queueCount: number; // existing resolve-tab aggregate; may include near/relation
  exactUnresolvedQueueCount: number; // finalize blocker source (G2)
  conflictCount: number;
  approvedCount: number;
  hasPendingApply: boolean;
};
```

### G4 Approved — 2026-06-02

Finalize **`reverify`** step is locked as:

1. **Resolve recount** — refresh resolve counts from `_review_rows_cache` only; recompute `exactUnresolvedQueueCount` (G2) and near/relation warning counts (G3); **do not** rerun exact/near/relation detection.
2. **Targeted quality reanalysis** — `issue_file_ids` = unique `file_id` from current quality index/cache; if non-empty → `reanalyze_quality_for_file_ids(issue_file_ids)`; if empty → skip file reads; then recompute `encodingIssueCount`, `integrityIssueCount`, `smallFileAnomalyCount`.
3. **Scan state** — read `work.scan.state` only; **do not** call `start_scan` or upgrade `SCAN_NOT_SUCCESS` inside finalize.
4. **Duplicate index** — trust persisted review state + `_review_rows_cache`; **no** hash recompute; **no** full duplicate detection.

**Finalize v1 MUST NOT:** `start_scan`; full filesystem rescan; near/relation detection; duplicate hash recompute; library-wide `analyze_quality(all files)`; mutate review row status during reverify.

**Authoritative result:** `precheck` is fast/advisory; **`reverify` is authoritative** — `FinalizeResult.blockers`, `FinalizeResult.warnings`, and the written report **MUST** use lists produced **after** reverify.

**Implementation:** `refresh_finalize_session_state(session)` in `finalize_runner.py` (see plan 017).

### G5 Approved — 2026-06-02

Cleanup v1 is **empty directory cleanup only**.

**Allowed cleanup roots** (library-root direct children): `duplicate/`, `organized/`. No files deleted. No arbitrary user folders. No library metadata folders.

**Allowed paths:** `{library_root}/duplicate/**`, `{library_root}/organized/**` — bottom-up removal of empty directories only.

**Forbidden:** `library_root` itself; arbitrary user-created folders; chosung/category folders outside `organized/`; `library_root/.novelguard/`; `~/.novelguard/**`; report/audit/backup/database/staging metadata.

**Runner (`cleanup_preview`):**

| `includeCleanup` | Blockers | Result |
|------------------|----------|--------|
| `false` | any | preview only (`previewedEmptyDirs`); `removedEmptyDirs = []` |
| `true` | ≥ 1 | skip cleanup (G1); `removedEmptyDirs = []` |
| `true` | 0 | remove empty allowlisted dirs bottom-up → `removedEmptyDirs` |

`cleanup.previewedEmptyDirs` and `cleanup.removedEmptyDirs` **MUST** always appear in `FinalizeResult` and report JSON. Empty candidate count is **not** a `FinalizeWarning` (G3).

**Implementation:** `CLEANUP_ALLOWED_ROOT_NAMES = frozenset({"duplicate", "organized"})` in `finalize_cleanup` port/infra; `Path.resolve()`; reject paths escaping `library_root` or whose first segment is not allowlisted.

**UI:** Checkbox default **unchecked**; label `빈 출력 폴더(duplicate/, organized/) 삭제`; helper `파일은 삭제하지 않고, 비어 있는 출력 폴더만 정리합니다.`; checked ⇒ `includeCleanup: true` (v1 confirm, no modal); blockers ⇒ checkbox + primary CTA disabled (B1).

### G6 Approved — 2026-06-02

Finalize completion does **not** lock the library.

After `status == "complete"` or `"complete_with_warnings"`:

- Write finalize report; set `work.finalize.lastReportId`, `lastStatus`, `lastRunAt`; update `blockerCount` and `warningCount`.
- Allow future `start_scan` / apply / repair / finalize runs — **`LIBRARY_BUSY` mutual exclusion only**.

**Finalize v1 MUST NOT:** introduce `libraryLocked`; block future scans/apply/repair after complete; auto-approve review rows; auto-clear quality issues; mutate unresolved near/relation rows; auto-switch tabs after completion.

**Re-run semantics:**

| Case | Expected |
|------|----------|
| Finalize again after `complete` | Allowed; new report |
| Scan after `complete` | Allowed; may change revision/state |
| Apply move/repair after `complete` | Allowed if normal preconditions pass |
| Finalize while scan/apply/repair running | `LIBRARY_BUSY` |
| Previous reports | Preserved under SAVE |
| `blocked` report | No lock; fix blockers and rerun |

**Snapshot (`work.finalize`):** `lastReportId`, `lastStatus` (`idle` \| `running` \| `complete` \| `complete_with_warnings` \| `blocked` \| `error`), `lastRunAt`, `blockerCount`, `warningCount`. `cancelled` → `lastStatus = "idle"`, no report (G1).

**Revision:** Bump `libraryRevision` **only** when cleanup removes ≥1 empty directory. Report write under `~/.novelguard/SAVE/` alone does **not** bump revision.

### B1 Approved — 2026-06-02

**Pre-run UX (`get_finalize_summary`):**

1. `blockers.length > 0` — disable **최종 검증 실행** + cleanup checkbox; red blocker list; tooltip = first blocker message; `data-state = "disabled"`.
2. `blockers.length == 0` && `warnings.length > 0` — enable CTA + checkbox; yellow warnings; `data-state = "warning"`.
3. Both zero — enable CTA + checkbox; `data-state = "ready"`.
4. `pipeline.phase == "finalize"` — disable CTA + checkbox; `data-state = "running"`.
5. No library — disable CTA + checkbox; `data-state = "empty"`.

**Bridge:** `run_finalize_verification` **MUST NOT** reject merely because summary blockers exist. Reject only `NO_LIBRARY`, `LIBRARY_BUSY`, invalid request. If invoked with blockers, runner returns `status: "blocked"` + report (G1).

**Post-run:** `complete` / `complete_with_warnings` → success/warning + report enabled; `blocked` → report + retry CTA when not busy; `error` → retry when not busy; `idle` → follow current summary; `running` → CTA/checkbox disabled.

**Labels:** Primary `최종 검증 실행`; secondary `완료 보고서 보기` enabled only when `work.finalize.lastReportId != null`.

---

## Position in program

| PR | Delivers |
|----|----------|
| PR-15/16 | Move apply + outcome UX |
| PR-22 | Repair apply + audit `repair_*` events |
| **PR-23** | **Finalize runner + report + UI** |
| PR-24 | Packaging |

Wave **D** per [001 PR-20..25 roadmap](../roadmap/001-2026-06-02-pr20-pr25-development-roadmap.md).

---

## Current baseline (code truth)

| Item | Today |
|------|--------|
| `WorkMode` | `"scan" \| "resolve" \| "quality"` only — **no** `finalize` |
| `build_snapshot` | resolve + quality counts; **no** `work.finalize` |
| Pipeline | Used for **scan** only (`phase: scan`) |
| Audit | `~/.novelguard/apply-audit.jsonl` — move + repair events |
| Repair backup | `~/.novelguard/SAVE/repair_backup/<sessionId>/` |
| Logs route | Placeholder UI |
| Finalize runner | **None** |

PR-23 must not weaken move/repair preview-apply or quality repair.

---

## Terminology

| Term | Meaning |
|------|---------|
| **Finalize run** | One execution of the 4-step background pipeline |
| **Blocker** | Condition that forbids `status: complete` |
| **Warning** | Informational; may yield `complete_with_warnings` |
| **Report** | Immutable JSON artifact written when `FinalizeResult.status` is `blocked`, `complete`, or `complete_with_warnings` |

---

## Snapshot extensions (additive)

```typescript
work: {
  // existing scan, resolve, quality ...
  finalize: {
    lastReportId: string | null;
    lastStatus: "idle" | "running" | "complete" | "complete_with_warnings" | "blocked" | "error";
    lastRunAt: string | null; // ISO-8601
    blockerCount: number;
    warningCount: number;
  };
}
```

`pipeline.phase` during finalize: `"finalize"` with `label` per step (Korean).

---

## Bridge contract

### New methods

```typescript
interface FinalizeSummary {
  libraryRevision: number;
  scanState: string;
  resolve: {
    queueCount: number;
    exactUnresolvedQueueCount: number;
    conflictCount: number;
    approvedCount: number;
    hasPendingApply: boolean;
  };
  quality: {
    encodingIssueCount: number;
    integrityIssueCount: number;
    smallFileAnomalyCount: number;
    hasPendingQualityRepair: boolean;
  };
  auditTail: {
    lastMoveApplyAt: string | null;
    lastRepairApplyAt: string | null;
    moveApplyCount: number;
    repairApplyCount: number;
  };
  blockers: FinalizeBlocker[];
  warnings: FinalizeWarning[];
}

interface RunFinalizeRequest {
  includeCleanup: boolean; // default false in v1 UI
}

interface FinalizeCleanupResult {
  previewedEmptyDirs: string[];
  removedEmptyDirs: string[];
}

type FinalizeResult =
  | {
      status: "complete" | "complete_with_warnings" | "blocked";
      reportId: string;
      reportPath: string; // relative to SAVE root for display
      libraryRevision: number;
      blockers: FinalizeBlocker[];
      warnings: FinalizeWarning[];
      cleanup: FinalizeCleanupResult;
    }
  | {
      status: "cancelled" | "error";
      reportId: null;
      reportPath: null;
      libraryRevision: number;
      blockers: FinalizeBlocker[];
      warnings: FinalizeWarning[];
      cleanup: FinalizeCleanupResult;
      errorMessage?: string;
    };

// get_finalize_summary() -> FinalizeSummary
// run_finalize_verification(request: RunFinalizeRequest) -> FinalizeResult
// get_finalize_report(reportId: string) -> FinalizeReportDocument
// cancel_finalize() -> void
```

Python snake_case: `get_finalize_summary`, `run_finalize_verification`, `get_finalize_report`, `cancel_finalize`.

### Errors (`FinalizeErrorCode`)

| Code | When |
|------|------|
| `LIBRARY_BUSY` | Scan/apply/repair/finalize already running |
| `NO_LIBRARY` | No folder selected |
| `REPORT_NOT_FOUND` | Unknown `reportId` |

---

## 4-step runner (B2)

| Step | `pipeline.label` (ko) | Action |
|------|------------------------|--------|
| 1 `precheck` | 사전 조건 확인 | Compute blockers/warnings from session; abort early if hard busy flags |
| 2 `reverify` | 상태 재검증 | G4: `refresh_finalize_session_state`; recompute blockers/warnings (authoritative) |
| 3 `cleanup_preview` | 정리 미리보기 | G5: list/remove empty dirs per allowlist when `includeCleanup` (skipped when blockers — G1) |
| 4 `report` | 보고서 저장 | Write JSON; update `work.finalize`; bump `libraryRevision` if cleanup removed dirs |

**Cancel:** checked between steps; `status: cancelled`; `reportId`/`reportPath` null (G1); pipeline → idle.

---

## Blocker / warning model

### `FinalizeBlocker` (G2 — approved)

```typescript
interface FinalizeBlocker {
  code:
    | "PENDING_MOVE_PREVIEW"
    | "PENDING_REPAIR_PREVIEW"
    | "SCAN_NOT_SUCCESS"
    | "UNRESOLVED_DUPLICATE_QUEUE"
    | "QUALITY_ERROR_ISSUES";
  message: string;
  count?: number; // UNRESOLVED_DUPLICATE_QUEUE: exact_unresolved_queue_count; QUALITY_ERROR_ISSUES: encoding+integrity
}
```

`UNRESOLVED_DUPLICATE_QUEUE.count` MUST equal `exact_unresolved_queue_count(session)`, not `work.resolve.queueCount`.

### `FinalizeWarning` (G3 — approved)

```typescript
interface FinalizeWarning {
  code:
    | "SMALL_FILE_ANOMALIES"
    | "UNREVIEWED_RELATION"
    | "NEAR_GROUPS_PRESENT";
  message: string;
  count?: number; // omitted from array when count would be 0
}
```

Helpers (plan 017): `near_unresolved_file_row_count`, `relation_unresolved_file_row_count` — same row filter as G3, symmetric with `exact_unresolved_queue_count`.

---

## Report artifact

Path:

```text
~/.novelguard/SAVE/finalize/<sessionId>/finalize_<YYYYMMDD>T<HHMMSS>Z.json
```

Minimum schema:

```json
{
  "reportId": "finalize-uuid",
  "sessionId": "...",
  "createdAt": "ISO-8601Z",
  "libraryRevision": 3,
  "status": "complete_with_warnings",
  "blockers": [],
  "warnings": [{ "code": "SMALL_FILE_ANOMALIES", "count": 2 }],
  "summary": { "...": "mirror FinalizeSummary" },
  "audit": { "moveApplyCount": 1, "repairApplyCount": 1 },
  "cleanup": { "previewedEmptyDirs": [], "removedEmptyDirs": [] }
}
```

---

## UI — `FinalizeWorkspace` (B1)

Full pre-run / post-run rules: **B1 Approved** above. Summary:

| Element | Behavior |
|---------|----------|
| Entry | Work tab **적용 · 검증** (`finalize`) |
| Summary cards | Scan, `exactUnresolvedQueueCount`, quality errors, audit tail |
| Blockers list | Red; summary blockers disable primary CTA + cleanup checkbox |
| Warnings list | Yellow; warnings alone do not disable CTA |
| Cleanup checkbox | G5; disabled when summary blockers or running |
| **최종 검증 실행** | Primary; `runFinalizeVerification({ includeCleanup })` |
| **완료 보고서 보기** | Secondary; enabled when `lastReportId != null` |
| Failure | Logs route link + `reportPath` copy |
| `data-state` | `empty` \| `ready` \| `running` \| `success` \| `warning` \| `error` \| `disabled` |

Copy per [DESIGN.md](../../../DESIGN.md): avoid bare `실행`; use `최종 검증 실행`.

---

## Application layer

| Module | Responsibility |
|--------|----------------|
| `application/finalize_summary.py` | Build `FinalizeSummary` from session + audit tail reader |
| `application/finalize_blockers.py` | Pure blocker/warning rules (domain-friendly) |
| `application/finalize_runner.py` | 4-step orchestration; cleanup port |
| `application/finalize_report.py` | Write/read report JSON |
| `application/ports/finalize_cleanup.py` | List/remove empty dirs; `CLEANUP_ALLOWED_ROOT_NAMES` |
| `infrastructure/finalize_cleanup.py` | FS bottom-up empty-dir walk under allowlist only |

**No** new SQLite tables in v1.

---

## Out of scope

| Item | Owner |
|------|--------|
| Packaging / installer | PR-24 |
| Shell FileDock | PR-25 |
| Full library rescan inside finalize | **Forbidden** in v1 (G4) |
| Small-file **deletion** | Future |
| Settings expert mode | — |
| Full Logs UI redesign | Minimal link only |
| New move/repair APIs | — |

---

## Acceptance criteria

- [ ] `get_finalize_summary` reflects live session counts + audit tail
- [ ] Blockers prevent `status: complete`
- [ ] `run_finalize_verification` writes report JSON under SAVE
- [ ] Cancel mid-run returns to idle without corrupting library
- [ ] `work.finalize` populated on snapshot after run
- [ ] Finalize blocked when `hasPendingApply` / `hasPendingQualityRepair`
- [ ] Move/repair/quality regressions pass
- [ ] `python scripts/verify_phase_completion.py` PASS

---

## Grill-me / review gate

**Complete** (2026-06-02): G1–G6 + B1–B4 approved. Implement per [plan 017](../plans/017-2026-06-02-pr23-finalize-cleanup-pipeline.md) after PR-22 baseline.

---

## Changelog

| Date | Change |
|------|--------|
| 2026-06-02 | Initial draft 011 from roadmap PR-23 + PR-22 baseline |
| 2026-06-02 | G1 approved; `FinalizeResult` discriminated union; blocked always writes report |
| 2026-06-02 | G2 approved; exact-only duplicate queue; explicit non-blockers; bridge errors separate |
| 2026-06-02 | G3 approved; warning codes + emission rules; `exactUnresolvedQueueCount` on summary |
| 2026-06-02 | G4 approved; reverify authoritative; targeted quality reanalyze; explicit prohibitions |
| 2026-06-02 | G5 approved; duplicate/organized empty-dir cleanup only; UI checkbox confirm |
| 2026-06-02 | G6 approved; no library lock; re-run semantics; revision bump on cleanup only |
| 2026-06-02 | B1 approved; UI disable on summary blockers; bridge allows blocked report |
| 2026-06-02 | Spec status → **approved** (grill-me complete) |
