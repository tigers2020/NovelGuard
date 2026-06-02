---
title: PR-22 Quality Repair Execution
status: approved
date: 2026-06-02
approved: 2026-06-02
authors: PR-22 spec gate + grill review 2026-06-02
parent_spec: docs/superpowers/specs/009-2026-06-02-quality-issue-detail-design.md
related_specs:
  - docs/superpowers/specs/001-2026-06-01-pr13-preview-token-stale-apply-design.md
  - docs/superpowers/specs/003-2026-06-01-real-apply-use-cases-design.md
roadmap: docs/superpowers/roadmap/001-2026-06-02-pr20-pr25-development-roadmap.md
pr_label: PR-22
plan: docs/superpowers/plans/016-2026-06-02-pr22-quality-repair-execution.md
prerequisite_commit: "[pr21] quality issue detail response and drawer UX"
---

# PR-22 — Quality Repair Execution

## Status

**Approved** (2026-06-02) — grill-me G1–G6 + blockers B1–B5 locked. **PR-21 baseline committed** before PR-22 implementation (`repairEligibility.eligible === false` in PR-21; PR-22 flips eligibility in its own slice).

## Scope sentence

PR-22 delivers **UTF-8 repair** for `invalid_utf8` quality issues via **preview → confirm → apply**, reusing the Wave A **frozen-plan / preview-token / revision / fingerprint** safety model from PR-13 and PR-15. It adds bridge methods, a repair planner, filesystem rewrite with **fileId-based backup**, audit events, and `RepairSubflowDialog`. v1 UI starts repair **only from Quality detail (single issue)**. No “repair all”, no batch-all button.

---

## Program locks (grill-me — approved 2026-06-02)

| Lock | Rule |
|------|------|
| **LOCK-1** | PR-22 supports **`invalid_utf8` only** — no empty/tiny/read_error execution |
| **LOCK-2** | v1 UI starts repair **only from detail row** — no grid “전체 복구” / repair-all |
| **LOCK-3** | API `issueIds` length **1..10**; v1 UI always sends **exactly 1** id |
| **LOCK-4** | `pendingPreview` (move) and `pendingQualityRepair` (repair) are **mutually exclusive** — symmetric reject |
| **LOCK-5** | `iso-8859-1` is **low-confidence fallback only** — never silent high-confidence; preview shows explicit warning |
| **LOCK-6** | `repairPreviewToken` binds **sessionId, libraryRevision, issueSelectionFingerprint, planFingerprint, immutable operations[]** |
| **LOCK-7** | Apply **revalidates drift** (revision, selection, plan fingerprint, per-file identity) before any write |
| **LOCK-8** | Backup path is **`fileId`-based** under `SAVE/repair_backup/<sessionId>/` — no raw path mirror |
| **LOCK-9** | Partial apply matches PR-15: prior successes remain; failure rejects with `REPAIR_FAILED`; audit both; **revision bumps if ≥1 success**; successful files re-analyzed |
| **LOCK-10** | Post-apply re-analysis is **file-scoped** — no full-library rescan |

---

## Grill-me decision log

| # | Topic | Lock | Status |
|---|--------|------|--------|
| G1 | Batch | API 1..10; **v1 UI detail 단건만**; repair-all 금지 | **Approved** |
| G2 | Encoding | `cp949` → `euc-kr` → `shift_jis` **strict**; then `iso-8859-1` **strict low-confidence** only (B1) | **Approved** |
| G3 | Pending | Move ↔ repair **상호 차단**; `MOVE_PREVIEW_ACTIVE` / `REPAIR_PREVIEW_ACTIVE` | **Approved** |
| G4 | Backup | `SAVE/repair_backup/<sessionId>/<fileId>/original.bin` + `metadata.json` (B3) | **Approved** |
| G5 | Index | Per-file re-analyze → quality row/detail refresh → `libraryRevision` bump | **Approved** |
| G6 | Errors | `RepairPreviewErrorCode` vs `RepairApplyErrorCode` — separate unions (G6) | **Approved** |

### Blocker resolution log

| # | Topic | Resolution | Status |
|---|--------|------------|--------|
| B1 | `iso-8859-1` mojibake | Low-confidence only; preview warning; normal confirm path; never auto high-confidence | **Locked** |
| B2 | Frozen plan | Token binds full pending state; apply revalidates revision, selection, planFingerprint, file identity | **Locked** |
| B3 | Backup traversal | fileId directory + metadata.json; no relative path mirror | **Locked** |
| B4 | Partial apply | Sequential ops; mixed preview reject; PR-15 partial semantics (LOCK-9) | **Locked** |
| B5 | Write sequence | 14-step apply sequence; temp in **same directory** as source (below) | **Locked** |

---

## PR-21 baseline boundary

| Item | PR-21 (committed) | PR-22 (this PR) |
|------|-------------------|-----------------|
| `repairEligibility.eligible` | `false` for all kinds | `true` for repairable `invalid_utf8` only |
| `getQualityIssueDetail` shape | unchanged | unchanged |
| File mutation | none | in-place UTF-8 rewrite |

Implementation **must not** modify PR-21 behavior in the same commit as repair execution unless explicitly rebasing; eligibility flip is PR-22 scope only.

---

## Encoding detection (G2 + B1)

### Candidates (strict decode)

1. `cp949` — confidence **`high`**
2. `euc-kr` — confidence **`high`**
3. `shift_jis` — confidence **`high`**
4. `iso-8859-1` — confidence **`low`** (fallback only)

All decodes use strict mode (`errors="strict"`). First **high-confidence** success wins. If none, try `iso-8859-1`; on success mark **`low`** and set `encodingWarning` on preview row.

### Preview row fields (additive)

```typescript
interface QualityRepairPreviewRow {
  issueId: string;
  action: "utf8_convert";
  relativePath: string;
  sourceEncoding: string;
  encodingConfidence: "high" | "low";
  encodingWarning?: string; // required when confidence === "low"
}
```

**UI:** low-confidence rows show warning copy before confirm; apply still allowed after checkbox (LOCK-5).

### Planner skip vs reject

| Case | Result |
|------|--------|
| `len(issueIds) > 10` | Preview reject `BATCH_LIMIT_EXCEEDED` |
| `len(issueIds) < 1` | Preview reject `EMPTY_SELECTION` |
| Any id not found / wrong kind / undetected encoding in request | Preview reject `MIXED_OR_INELIGIBLE_SELECTION` (**no partial preview**) |
| All ids valid `invalid_utf8` with detected encoding | Preview success with `operationCount === issueIds.length` |

---

## Frozen pending plan (B2)

`repairPreviewToken` is an opaque id into server `PendingQualityRepair`:

```text
PendingQualityRepair {
  token: string
  sessionId: string
  libraryRevision: number
  issueSelectionFingerprint: string
  planFingerprint: string
  repairOperations: RepairOperation[]  // immutable at store time
}
```

### Apply validation (hard — before any FS write)

```text
if current libraryRevision !== pending.libraryRevision:
  reject STALE_REPAIR_PREVIEW

if request issueSelectionFingerprint !== pending.issueSelectionFingerprint:
  reject ISSUE_SELECTION_CHANGED

if recomputed planFingerprint(operations) !== pending.planFingerprint:
  reject PLAN_MISMATCH

for each operation:
  if file size / contentHash / mtimeNs drift from operation snapshot:
    reject STALE_REPAIR_PREVIEW  // no batch mutation
```

`RepairOperation` includes `fileId`, `issueId`, `relativePath`, `sourceEncoding`, `encodingConfidence`, `sourceSize`, `sourceContentHash`, `sourceMtimeNs?`.

---

## Bridge contract

### New methods

```typescript
interface QualityRepairPreviewRequest {
  issueIds: string[];
}

interface QualityRepairPreviewSummary {
  issueCount: number;
  operationCount: number;
}

interface QualityRepairPreviewResult {
  repairPreviewToken: string;
  libraryRevision: number;
  issueSelectionFingerprint: string;
  hasPendingQualityRepair: true;
  rows: QualityRepairPreviewRow[];
  summary: QualityRepairPreviewSummary;
}

interface ApplyQualityRepairRequest {
  issueIds: string[];
  repairPreviewToken: string;
}

// discardQualityRepairPreview({ repairPreviewToken }) → Promise<void>  // idempotent
```

Python: `get_quality_repair_preview`, `apply_quality_repair`, `discard_quality_repair_preview`.

### Mutual exclusion (G3 / LOCK-4)

| Active pending | Blocked call | Code |
|----------------|--------------|------|
| Move `pendingPreview` | repair preview / apply | `MOVE_PREVIEW_ACTIVE` |
| Repair `pendingQualityRepair` | move preview / apply | `REPAIR_PREVIEW_ACTIVE` |

### Error codes — preview phase

`RepairPreviewErrorCode` (throw on `get_quality_repair_preview`):

| Code | When |
|------|------|
| `BATCH_LIMIT_EXCEEDED` | `issueIds.length > 10` |
| `EMPTY_SELECTION` | `issueIds.length < 1` |
| `MIXED_OR_INELIGIBLE_SELECTION` | Any ineligible / not found / undetected encoding in request |
| `MOVE_PREVIEW_ACTIVE` | Move preview pending |
| `REPAIR_PREVIEW_ACTIVE` | Repair preview already pending (new preview replaces — see below) |
| `LIBRARY_BUSY` | Scan or apply in progress |

**Single repair pending slot:** new successful preview **replaces** prior repair pending (parity move preview).

### Error codes — apply phase

`RepairApplyErrorCode` (throw on `apply_quality_repair`):

| Code | When |
|------|------|
| `STALE_REPAIR_PREVIEW` | Revision / file identity drift |
| `ISSUE_SELECTION_CHANGED` | `issueIds` or fingerprint mismatch |
| `PLAN_MISMATCH` | Recomputed plan fingerprint mismatch |
| `NO_PENDING_REPAIR` | No pending repair |
| `MISSING_REPAIR_PREVIEW_TOKEN` | Empty token |
| `INVALID_REPAIR_PREVIEW_TOKEN` | Unknown token |
| `REPAIR_FAILED` | Batch abort; include partial success details |
| `LIBRARY_BUSY` | Concurrent scan/apply |
| `MOVE_PREVIEW_ACTIVE` | Move preview pending |

Transport: `BridgeCallError` with `code: "rejected"` + `reason`.

---

## Apply sequence (B5)

Per operation, after validations:

1. Validate `repairPreviewToken` and frozen plan
2. Re-stat source file under `library_root`
3. Read original bytes
4. Verify `fileId`, size, `sourceContentHash`, `sourceMtimeNs` vs operation
5. Decode using `sourceEncoding` (**strict**)
6. Encode UTF-8
7. Write backup: `SAVE/repair_backup/<sessionId>/<fileId>/original.bin` + `metadata.json`
8. Write temp UTF-8 file **in same directory** as source: `<basename>.novelguard-repair.tmp`
9. Flush / fsync best-effort
10. Atomic replace temp → original
11. On replace failure: **original must remain intact** (temp discarded)
12. Re-read file; re-analyze quality for that `fileId` only
13. Audit `repair_applied` (per op) or `repair_failed`
14. After batch: bump `libraryRevision` if ≥1 success; audit `repair_completed` or batch-level `repair_failed`

**No automatic rollback** (v1).

---

## Backup layout (B3 / LOCK-8)

```text
SAVE/repair_backup/<sessionId>/<fileId>/
  original.bin
  metadata.json
```

`metadata.json`:

```json
{
  "fileId": "...",
  "originalPath": "relative/path.txt",
  "sourceEncoding": "cp949",
  "encodingConfidence": "high",
  "sourceSize": 12345,
  "sourceMtimeNs": 123456789,
  "backupCreatedAt": "ISO-8601Z",
  "repairPreviewToken": "..."
}
```

No `..`, no drive-letter path segments in directory names; **fileId** is sole directory key.

---

## Partial apply (B4 / LOCK-9)

**Preview:** all requested ids must be repairable — otherwise **reject** (no `skippedCount` in v1 success path).

**Apply:**

- Operations run **sequentially**
- On operation *i* failure: operations `1..i-1` remain committed; audit success + failure rows; throw `REPAIR_FAILED` with `partialSuccess`, `succeededCount`, `failedIssueId`
- `libraryRevision` bumps if ≥1 success
- Re-analyze **only** files with successful applies
- Failed and unexecuted operations: filesystem unchanged

---

## Audit log

| Event | When |
|-------|------|
| `repair_preview_created` | After successful preview (stores frozen plan) |
| `repair_started` | After apply validation, before first FS op |
| `repair_applied` | Per successful operation |
| `repair_failed` | Per failed op or batch abort |
| `repair_completed` | Batch end (all success) |

Fields: `repairPreviewToken`, `sessionId`, `issueId`, `fileId`, `relativePath`, `sourceEncoding`, `encodingConfidence`, `backupPath`, `outcome`, `error?`.

Same JSONL file as move apply; outside scanned library tree.

---

## UI (LOCK-2)

- Entry: Quality detail **「복구 미리보기」** when `repairEligibility.eligible === true`
- `RepairSubflowDialog`: preview → confirm (checkbox) → apply → done
- v1 passes `issueIds: [selectedRow.id]` only
- Low-confidence warning visible on confirm step
- Cancel/close → `discardQualityRepairPreview` (idempotent)
- Stale: `issue_selection_changed` \| `library_changed` (client + bridge)

**Forbidden:** grid toolbar “전체 복구”, default repair-all, repair without preview.

---

## PR-22 eligibility change

`_repair_eligibility_for_kind` in PR-22:

| Kind | `repairEligibility` |
|------|---------------------|
| `invalid_utf8` | `{ eligible: true, reason: "ready", futureAction: "utf8_convert", label: "…" }` when file exists in snapshot |
| others | unchanged from PR-21 (`eligible: false`) |

---

## Out of scope

| Item | Owner |
|------|--------|
| empty/tiny/read_error repair | Future |
| Relation / near / duplicate repair | — |
| Repair-all / default batch | — |
| charset PyPI dependency | v2 |
| Finalize wiring | PR-23 |
| PR-21 contract shape changes | — |

---

## Acceptance criteria

- [ ] PR-21 commit on branch before PR-22 code lands
- [ ] Preview rejects mixed/ineligible selection and `len > 10`
- [ ] Frozen plan + apply drift checks (LOCK-6, LOCK-7)
- [ ] `iso-8859-1` preview shows low-confidence warning
- [ ] Backup fileId layout; temp replace failure leaves original intact
- [ ] Partial apply semantics (LOCK-9)
- [ ] Move ↔ repair mutual exclusion
- [ ] Post-repair file-scoped re-analyze; `invalid_utf8` row cleared
- [ ] `python scripts/verify_phase_completion.py` PASS

---

## Changelog

| Date | Change |
|------|--------|
| 2026-06-02 | Initial draft 010 |
| 2026-06-02 | Grill-me G1–G6 + B1–B5; LOCK-1..10; **approved** |
