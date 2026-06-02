---
title: PR-21 Quality Issue Detail
status: approved
date: 2026-06-02
approved: 2026-06-02
authors: PR-21 spec gate + codebase baseline
parent_spec: docs/superpowers/specs/002-2026-06-01-novelguard-greenfield-library-session-design.md
related_specs:
  - docs/superpowers/specs/006-2026-06-01-duplicate-group-detail-design.md
  - docs/superpowers/specs/008-2026-06-02-relation-filename-blocking-design.md
roadmap: docs/superpowers/roadmap/001-2026-06-02-pr20-pr25-development-roadmap.md
pr_label: PR-21
plan: docs/superpowers/plans/015-2026-06-02-pr21-quality-issue-detail.md
---

# PR-21 — Quality Issue Detail

## Status

**Approved** (2026-06-02) — **Implemented** per [plan 015](../plans/015-2026-06-02-pr21-quality-issue-detail.md) (2026-06-02).

## Scope sentence

PR-21 delivers a **typed**, **revision-aware** `getQualityIssueDetail(issueId)` built from scan-time `QualityIssue` domain records plus `FileRecord` metadata, and upgrades the Quality workspace detail drawer to show evidence, file facts, repair eligibility (read-only labels), and stable **not-found** / **stale** UX. It does **not** execute UTF-8 repair, mutate files, or add batch repair (PR-22).

## Locked decisions (brainstorming — pre–grill-me)

| Item | Lock |
|------|------|
| Mutation | **None** — read-only detail + UI |
| Detail source | Current scan snapshot: `_quality_rows_cache` row lookup + `_index.quality_issues()` for domain `evidence` + `_files_by_id` for file metadata |
| Issue id | Bridge id = `quality:{issue_id}` where `issue_id = make_issue_id(file_id, kind)` (unchanged from PR-14c) |
| Bridge response | `QualityIssueDetailResponse` = `ok` \| `not_found` — `ok` wraps inner `detail: QualityIssueDetail` |
| Unknown id | **`status: "not_found"`**, `message: "quality_issue_not_found"` — remove legacy flat `Unknown` success object |
| Revision | `ok.detail.libraryRevision` from `LibrarySession.library_revision()` at build time |
| Stale UX | **Client-owned** — no server `stale` union; compare `detail.libraryRevision` vs `snapshot.libraryRevision` after fetch (§ G2) |
| Post-scan refresh | `startScan` completion / snapshot bump invalidates open detail (same as grid reload) |
| Repair execution | **Forbidden** — `repairEligibility.eligible === false` for all kinds in PR-21 |
| Repair labels | Show **why** ineligible or “PR-22” for kinds that will become eligible (`invalid_utf8` only) |
| Evidence | Typed `IssueEvidence` from domain `QualityIssue.evidence` + derived display fields — not `Record<string, unknown>` in TS |
| Raw JSON | **Dev-only** behind `import.meta.env.DEV` toggle — hidden in production UI |
| Bridge validation | New `validate_quality_issue_detail` in `bridge_contract.py`; called from `BridgeApi.get_quality_issue_detail` |
| APIs | **Extend `getQualityIssueDetail` only** — no new bridge methods |
| Tests | Extend `tests/test_bridge_contract.py` + `mockBridge` — no new test files without `TEST_ALLOWED` |

### Grill-me decision log

| # | Topic | Lock |
|---|--------|------|
| G1 | Not-found vs placeholder | **Approved 2026-06-02** — `unknown issueId` → `{ status: "not_found", id, message: "quality_issue_not_found" }`; **remove** legacy flat `Unknown` success object; update contract tests + mockBridge |
| G2 | Stale detection | **Approved 2026-06-02** — no server `stale` union; `ok.detail.libraryRevision`; client compares to `snapshot.libraryRevision`; banner `quality-detail-stale` (§ G2) |
| G3 | Evidence typing | **`IssueEvidence`** per `QualityKind` — common fields + kind-specific optional keys; validate on bridge |
| G4 | `invalid_utf8` repair label | `repairEligibility: { eligible: false, reason: "repair_not_implemented", futureAction: "utf8_convert" }` |
| G5 | Detail fetch errors | Bridge throw → Quality workspace **detail error** strip (parity with `quality-query-error`), not silent empty |
| G6 | Row id normalization | Accept `issueId` with or without `quality:` prefix; normalize to cache id before lookup |

### Spec gate review checklist (pre-approval)

| # | Blocker | Status |
|---|---------|--------|
| B1 | Not-found union documented + migration from Unknown placeholder | **Locked (G1 approved 2026-06-02)** |
| B2 | `libraryRevision` on `ok.detail` | **Locked (G2 approved 2026-06-02)** |
| B3 | Stale UX client-owned; no server `stale` | **Locked (G2 approved 2026-06-02)** |
| B4 | PR-22 boundary (no preview token / no apply) | Locked out of scope |
| B5 | Evidence fields match `quality_analyzer` today | Mapped in § Evidence by kind |

---

## Position in program

| PR | Delivers |
|----|----------|
| PR-14c | `analyze_quality`, `QualityIssue`, row builder |
| PR-14d | `queryQualityRows` real bridge + error UX |
| PR-20 | Relation track closed |
| **PR-21** | **Rich quality detail DTO + drawer UX** |
| PR-22 | Repair preview / apply |

Wave **D** per [001 PR-20..25 roadmap](../roadmap/001-2026-06-02-pr20-pr25-development-roadmap.md).

---

## Current baseline (code truth)

| Item | Today |
|------|--------|
| `get_quality_issue_detail` | Cache row only; `evidence: { severity }`; missing id → **success** placeholder `Unknown` |
| `QualityIssue` in index | Full `evidence` dict in SQLite / memory via `quality_issues()` — **not** joined in detail |
| TS types | Flat `QualityIssueDetail`, no `QualityIssueDetailResponse` ([quality.ts](../../../web/src/types/quality.ts)) |
| `bridge_contract` | Validates `QualityRowsPage` only — **no** detail validator |
| `QualityWorkspace` | Fetches detail on select; shows name/path/suggestedAction only |
| `mockBridge.getQualityIssueDetail` | Same placeholder behavior as Python |

PR-21 must not weaken `queryQualityRows` or scan-time quality detection.

---

## Terminology

| Term | Meaning |
|------|---------|
| **Quality row id** | Bridge id `quality:{issue_id}` used in grid and detail request |
| **Domain issue id** | `make_issue_id(file_id, kind)` — hex digest |
| **Issue type (UI)** | `integrity` \| `encoding` \| `small_file` — grid tab filter |
| **Quality kind (domain)** | `empty_file` \| `tiny_file` \| `invalid_utf8` \| `read_error` |
| **Repair eligibility** | Read-only hint whether PR-22 may offer repair — not executable in PR-21 |

### Kind → issue type mapping (unchanged from PR-14c)

| `QualityKind` | `issueType` | `integrity` label (row) |
|---------------|-------------|-------------------------|
| `read_error` | `integrity` | Read error |
| `invalid_utf8` | `encoding` | Decode error |
| `empty_file` | `small_file` | Empty file |
| `tiny_file` | `small_file` | Very small file |

---

### G2 — Stale detail (approved 2026-06-02)

Quality issue detail lookup **MUST NOT** return a server-side `stale` union in PR-21.

The `ok` response **MUST** include `detail.libraryRevision`.

The client **MUST** compare `detail.libraryRevision` against the current `snapshot.libraryRevision` immediately after fetch/render.

If the values differ, the UI **MUST** render a stale banner with `data-testid="quality-detail-stale"` and **MUST NOT** present the detail as current. Stale detail remains read-only; show refetch/refresh guidance.

The stale state is client-owned because the bridge does not receive an `expectedLibraryRevision` input in PR-21.

---

## `QualityIssueDetailResponse` contract

### TypeScript (`web/src/types/quality.ts`)

```typescript
export interface IssueEvidenceBase {
  kind: QualityKind; // domain kind
  message: string;
  severity: "warning" | "error";
  sizeBytes: number;
}

export interface IssueEvidenceEmptyFile extends IssueEvidenceBase {
  kind: "empty_file";
}

export interface IssueEvidenceTinyFile extends IssueEvidenceBase {
  kind: "tiny_file";
  thresholdBytes: number;
}

export interface IssueEvidenceInvalidUtf8 extends IssueEvidenceBase {
  kind: "invalid_utf8";
  decodeError?: string;
}

export interface IssueEvidenceReadError extends IssueEvidenceBase {
  kind: "read_error";
  error?: string;
}

export type QualityKind =
  | "empty_file"
  | "tiny_file"
  | "invalid_utf8"
  | "read_error";

export type IssueEvidence =
  | IssueEvidenceEmptyFile
  | IssueEvidenceTinyFile
  | IssueEvidenceInvalidUtf8
  | IssueEvidenceReadError;

export interface RepairEligibility {
  eligible: false;
  reason:
    | "repair_not_implemented"
    | "issue_not_repairable"
    | "read_error";
  futureAction?: "utf8_convert";
  label: string; // Korean UI string source — map in presentation layer
}

/** Inner detail payload (nested under `ok`). */
export interface QualityIssueDetail {
  id: string;
  libraryRevision: number;
  issueType: QualityIssueType;
  name: string;
  path: string;
  encoding: string;
  integrity: string;
  severity: "warning" | "error";
  suggestedAction: string;
  file: {
    fileId: string;
    sizeBytes: number;
    modifiedAtNs: number;
    extension: string;
    contentSha256: string;
  };
  evidence: IssueEvidence;
  repairEligibility: RepairEligibility;
}

export type QualityIssueDetailResponse =
  | {
      status: "ok";
      detail: QualityIssueDetail;
    }
  | {
      status: "not_found";
      id: string;
      message: "quality_issue_not_found";
    };
```

### Python

Same keys in `camelCase` JSON. `ok` → `{ "status": "ok", "detail": { … } }`. `BridgeApi.get_quality_issue_detail` validates via `validate_quality_issue_detail`. **Forbidden in PR-21:** `{ "status": "stale", … }`.

### Field rules (`ok.detail`)

| Field | Source |
|-------|--------|
| `id` | Normalized `quality:{issue_id}` matching grid row |
| `libraryRevision` | `session.library_revision()` at build time |
| `issueType` / `integrity` / `severity` / `suggestedAction` | Quality row cache |
| `name` | `FileRecord.name` or basename of path |
| `path` | `QualityIssue.path` (relative) |
| `encoding` | `"UTF-8"` unless kind is `invalid_utf8` or `read_error` → `"Unknown"` |
| `file.*` | `FileRecord` for `issue.file_id` |
| `evidence` | Built from `QualityIssue` domain row (see § Evidence builder) |
| `repairEligibility` | Static policy table § Repair eligibility |

### `not_found`

| Field | Rule |
|-------|------|
| `status` | Always `"not_found"` |
| `id` | Echo normalized request id |
| `message` | Always `"quality_issue_not_found"` |

---

## Evidence builder (application)

New module: `src/application/quality_issue_detail.py`

```python
def normalize_quality_issue_id(issue_id: str) -> str:
    trimmed = issue_id.strip()
    if trimmed.startswith("quality:"):
        return trimmed
    return f"quality:{trimmed}"


def build_quality_issue_detail(
    issue_id: str,
    *,
    quality_rows: list[dict[str, Any]],
    quality_issues: list[QualityIssue],
    files_by_id: dict[str, FileRecord],
    library_revision: int,
) -> dict[str, Any]:
    ...
```

Lookup steps:

1. Normalize id (G6).
2. Find row in `quality_rows` by `id`.
3. If missing → `not_found`.
4. Parse domain `issue_id` from row id (`quality:` prefix strip).
5. Find `QualityIssue` where `issue.issue_id == domain_id` (first match).
6. Load `FileRecord` via `issue.file_id`.
7. Build `evidence` + `repairEligibility` from kind.
8. Return `{ "status": "ok", "detail": { … } }`.

---

## Evidence by kind

| Kind | `evidence` keys (minimum) |
|------|---------------------------|
| `empty_file` | `sizeBytes: 0` |
| `tiny_file` | `sizeBytes`, `thresholdBytes` from domain evidence |
| `invalid_utf8` | `sizeBytes`, `decodeError` from domain evidence |
| `read_error` | `sizeBytes`, `error` from domain evidence |

Domain `message` → `evidence.message`. Domain `severity` → `evidence.severity`.

---

## Repair eligibility (read-only)

| `QualityKind` | `repairEligibility` |
|---------------|---------------------|
| `invalid_utf8` | `{ eligible: false, reason: "repair_not_implemented", futureAction: "utf8_convert", label: "…" }` |
| `empty_file` | `{ eligible: false, reason: "issue_not_repairable", label: "…" }` |
| `tiny_file` | `{ eligible: false, reason: "issue_not_repairable", label: "…" }` |
| `read_error` | `{ eligible: false, reason: "read_error", label: "…" }` |

UI: show badge **복구 예정 (PR-22)** only when `futureAction === "utf8_convert"`. No preview/apply buttons.

---

## UI behavior (`QualityWorkspace`)

| Event | Behavior |
|-------|----------|
| Row select | `getQualityIssueDetail(row.id)` → if `ok`, use `payload.detail`; if `not_found`, not-found panel |
| Fetch error | `detailError` string + retry (`quality-detail-error`, `quality-detail-retry`) |
| Stale | After fetch, if `payload.status === "ok"` and `payload.detail.libraryRevision !== snapshot.libraryRevision` → `quality-detail-stale` banner; do not present detail as current; read-only; refetch/refresh CTA |
| Scan complete | Existing `loadPage` reset clears selection — detail follows first row |
| Dev raw JSON | Collapsible `<pre>` only when `import.meta.env.DEV` |

Presentation: Korean labels for severity, kind, eligibility (map in component — not bridge).

---

## Out of scope

| Item | Owner |
|------|--------|
| UTF-8 conversion / file rewrite | PR-22 |
| `repairPreviewToken` | PR-22 |
| Batch repair | PR-22 |
| Quality grid layout redesign | Optional polish — not required |
| New SQLite tables | None |
| Relation / duplicate detail changes | — |

---

## Acceptance criteria

- [ ] `getQualityIssueDetail` returns `QualityIssueDetailResponse`; bridge validates
- [ ] Unknown id → `not_found` with `message: "quality_issue_not_found"` — no `Unknown` success object
- [ ] `ok.detail` includes `libraryRevision`, full `evidence`, `file`, `repairEligibility`
- [ ] No `{ status: "stale" }` in bridge responses (PR-21)
- [ ] Domain evidence round-trips for all four kinds (contract fixtures)
- [ ] Stale banner when revision drifts (client test or E2E hook)
- [ ] Detail fetch failure surfaces error + retry
- [ ] `queryQualityRows` regression-free
- [ ] `python scripts/verify_phase_completion.py` PASS

---

## Grill-me / review gate (human)

| Item | Status |
|------|--------|
| G1 not-found union | **Approved** 2026-06-02 |
| G2 client-side stale | **Approved** 2026-06-02 |
| B1–B5 | **Locked** |

**Next:** Plan 015 human approval → implement.

---

## Changelog

| Date | Change |
|------|--------|
| 2026-06-02 | Initial draft 009 from roadmap PR-21 + code baseline |
| 2026-06-02 | G1 approved — `not_found` union; legacy Unknown success removed |
| 2026-06-02 | G2 approved — `ok.detail.libraryRevision`; client stale UX; no server `stale` union |
| 2026-06-02 | Spec **approved**; response shape `QualityIssueDetailResponse` with nested `detail` |
| 2026-06-02 | Implemented per plan 015 |
