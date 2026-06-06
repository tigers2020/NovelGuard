---
title: Apply preview display rows — filename and move path in confirm step
status: draft
date: 2026-06-05
implementation: wip-on-branch
wip_branch: wip/mixed-035-036-salvage
risk: safe
kind: feature
layer: crosslayer
area: work
tags:
  - apply
  - move-preview
  - ux
  - bridge-contract
related_specs:
  - docs/superpowers/specs/033-2026-06-05-auto-keeper-bulk-approve-policy.md
---

> **Status:** `draft` / **not on main** — implementation preserved on `wip/mixed-035-036-salvage`
> **Current main contract:** [main-ux-contract.md](../../architecture/main-ux-contract.md)
> **Target PR:** `feature/apply-preview-display-rows` — move/apply preview only; do not mix with bulk auto-approve job.

# Apply preview display rows

## Summary

The Apply subflow confirm step (`이동 계획 적용` → step 2) currently lists opaque review row IDs (`file:dup-…`, `file:relation:…`). Users cannot verify what will move before applying.

This spec enriches `get_move_preview` row payloads with human-readable fields and updates the confirm table to show **filename** and **source → destination path** only (option B).

## Problem

| Layer | Today |
|-------|--------|
| UI | `PreviewRowsTable` columns: `행 ID`, `동작` |
| Bridge `MovePreviewRow` | `{ id, action }` only |
| Backend | `BuildPreviewPlanUseCase` already computes `file_record.name`, `source_path`, `dest_path` in `PreviewOperation` but does not expose them in `rows[]` |

Users with 99+ move targets see unusable hashes instead of novel filenames and paths.

## Goals

| Goal | Pass condition |
|------|----------------|
| Readable confirm list | Each preview row shows filename + `sourcePath → destPath` |
| Server-authoritative | Display data comes from preview response, not client grid join |
| Apply unchanged | `previewToken`, `PreviewOperation`, and apply keyed by `id` unchanged |
| Large selections | Existing scroll container (`max-h-48`) sufficient for v1 |

## Locked UX (option B)

Confirm table columns:

| Column | Content |
|--------|---------|
| **파일** | `name` — file basename / novel title (`title` attribute for full string) |
| **이동 경로** | `{sourcePath} → {destPath}` — relative paths, monospace, truncates with scroll |

Not in table (unchanged):

- Row `id` — hidden from primary UI; retained for `data-testid`, apply, audit
- `action` column — removed from UI (always `move_duplicate` for listed rows)
- Conflict/blocked rows — remain summary chips only (`실행`, `미리보기 행`, `충돌`)

## Non-goals

- Resolve grid parity columns (type, keeper, size, encoding)
- Conflict/blocked detail rows in the same table
- Virtualized table or pagination in confirm step
- Second bridge call for display metadata
- Client-side join of preview ids to loaded Resolve grid rows

## Recommended architecture

**Approach A — enrich `get_move_preview` rows** (selected).

Rejected:

| Approach | Reason |
|----------|--------|
| UI joins preview ids to loaded grid rows | Fails on partial load / 7k libraries |
| Separate display bridge method | Extra round-trip; YAGNI |

## Bridge contract

### `MovePreviewRow` extension

TypeScript (`web/src/types/movePreview.ts`):

```ts
export interface MovePreviewRow {
  id: string;
  action: string;
  name: string;
  sourcePath: string;
  destPath: string;
}
```

Python preview row dict (`build_preview_plan.py`):

```python
{
    "id": op.row_id,
    "action": "move_duplicate",
    "name": file_record.name,
    "sourcePath": op.source_path,
    "destPath": op.dest_path,
}
```

Field rules:

- `name`, `sourcePath`, `destPath` — required non-empty strings on every item in `rows[]`
- `id`, `action` — unchanged semantics for apply and audit
- Paths are library-relative POSIX-style strings (same as `PreviewOperation.source_path` / `dest_path`)

### Validation

| Location | Requirement |
|----------|-------------|
| `src/app/bridge_contract.py` `validate_move_preview` | Each row dict contains `name`, `sourcePath`, `destPath` as non-empty strings |
| `web/src/contracts/movePreviewContract.ts` | Same checks on `rows[]` elements |

Additive contract change: existing `id` + `action` consumers remain valid.

## UI changes

Target: `web/src/features/work/ApplySubflowDialog.tsx` — `PreviewRowsTable`.

| Before | After |
|--------|-------|
| Header `행 ID` | Header `파일` |
| Header `동작` | Header `이동 경로` |
| Cell `row.id` (mono) | Cell `row.name` (truncate) |
| Cell `row.action` | Cell `{row.sourcePath} → {row.destPath}` (mono xs) |

Keep `data-testid={`apply-preview-row-${row.id}`}` on `<tr>`.

Korean copy aligns with DESIGN.md microcopy rules.

## Backend changes

| File | Change |
|------|--------|
| `src/app/build_preview_plan.py` | Add display fields when appending to `preview_rows` |
| `src/app/bridge_contract.py` | Validate new row fields |

No changes to:

- `domain.apply_models.PreviewOperation`
- `PreviewApplyGuard` stored operations
- `ApplyResolvedActionsUseCase` execution path

## Mock bridge

`web/src/bridge/mockBridge.ts` — `buildMockPreviewPlan` must populate `name`, `sourcePath`, `destPath` from resolved `ReviewRow` data (name + path + target folder).

## Testing

| Layer | Cases |
|-------|-------|
| Python contract | `validate_move_preview` accepts enriched rows; rejects missing `name` |
| `test_real_move_preview_lists_duplicate_member` | Assert `name`, `sourcePath`, `destPath` present |
| Web contract | `validateMovePreviewResult` row field checks |
| UI | `ApplySubflowDialog` / table test: no visible row id column header |
| E2E | Apply confirm step shows filename text, not `file:dup-` prefix |

## Code touch map

| Area | Path |
|------|------|
| Spec | `docs/superpowers/specs/036-2026-06-05-apply-preview-display-rows-design.md` |
| Preview build | `src/app/build_preview_plan.py` |
| Contract | `src/app/bridge_contract.py` |
| Types | `web/src/types/movePreview.ts` |
| Web contract | `web/src/contracts/movePreviewContract.ts` |
| UI | `web/src/features/work/ApplySubflowDialog.tsx` |
| Mock | `web/src/bridge/mockBridge.ts` |
| Tests | `tests/test_bridge_contract.py`, web unit/e2e as needed |

## Acceptance criteria

| # | Criterion |
|---|-----------|
| 1 | Confirm step table headers are `파일` and `이동 경로` |
| 2 | No primary column shows raw `file:…` row id |
| 3 | Each listed row shows `name` and `sourcePath → destPath` from server preview |
| 4 | Apply with `previewToken` still succeeds; operations unchanged |
| 5 | Summary chips for conflicts/blocked unchanged |
| 6 | Contract tests enforce required display fields on preview rows |

## Out of scope

- Enriching apply success panel with per-file list
- Move preview step 1 label changes beyond table content
- Localizing `action` enum in UI
