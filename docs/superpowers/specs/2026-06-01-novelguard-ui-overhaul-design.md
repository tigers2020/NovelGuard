---
title: NovelGuard UI Overhaul — Hybrid Mode-Based Workspace
status: approved
date: 2026-06-01
authors: product + IA review (brainstorming)
reference_mock: Sample/MockUp/MockUp.jsx
design_tokens: DESIGN.md
ui_root: web/
---

# NovelGuard UI Overhaul — Design Spec

## Status

**Approved** (2026-06-01) — gate review augmentations applied. Ready for implementation plan (`writing-plans`).

## Summary

NovelGuard UI is rebuilt as **React + Tailwind v4** (`web/`) behind **pywebview** with a **Hybrid, mode-based Work route**. The primary review surface is **not** a four-card dashboard; it is a **Resolve & Organize** workspace that merges duplicate review and move planning into one **decision queue**, backed by **query APIs** and a **virtualized grid**. Full file rows are **never** embedded in `AppSnapshot`.

---

## Locked decisions (P0)

| Decision | Value |
|----------|--------|
| IA | **Hybrid** — mode-based workspaces + subflow-only wizard |
| Work structure | **3 modes:** Scan · Resolve & Organize · Quality |
| Duplicate + Move | **Merged** in Resolve & Organize (single decision queue) |
| Quality / Integrity | **Separate mode** — not mixed with organize decisions |
| File list (canonical) | **Shell summary strip** + **full review in Work-owned workspace** (not modal `FileListSheet` as primary UI) |
| Progress | **`GlobalCommandBar` only** — no per-section or footer progress |
| Wizard / Stepper | **Subflow only** (pipeline auto-run, destructive apply) |
| Data in snapshot | **Summaries only**; grids are **query-backed + virtualized** |
| Safety (AGENTS.md) | Destructive ops: **dry-run preview → user confirm → apply** |
| Qt / QSS | **Out of scope** for this generation — React-only UI |
| Reference mock | `Sample/MockUp/MockUp.jsx` (non-production; informs layout) |
| Grid stack (v1) | **TanStack Virtual + TanStack Table** (see criteria below) |
| Selection (P0.5) | **`SelectionScope` contract** — required for BatchActionBar |

### Canonical statement

```text
The primary Work UI is not a four-card dashboard.
It is a mode-based hybrid workspace:

1. Scan
2. Resolve & Organize
3. Quality

Resolve & Organize is the main review workspace and combines duplicate review,
keeper decisions, move planning, conflict review, and batch apply.

Large file lists must be rendered through a virtualized, query-backed grid.
Full file rows are never stored in AppSnapshot.
```

---

## App shell

```
┌─────────────────────────────────────────────────────────────┐
│ AppHeader                                                    │
├──────────┬──────────────────────────────────────────────────┤
│ AppSidebar │ RouteContent (Work | Settings | Logs)        │
├──────────┴──────────────────────────────────────────────────┤
│ FileSummaryStrip (global library awareness)                  │
│  folder · file count · size · dup groups · integrity · CTA   │
├─────────────────────────────────────────────────────────────┤
│ GlobalCommandBar (single progress + phase + cancel)          │
└─────────────────────────────────────────────────────────────┘
```

### FileSummaryStrip

Lightweight, always visible on Work+ (and minimal summary on Settings/Logs):

- Selected folder path (truncated)
- File count, total size
- Duplicate group count, integrity issue count
- **CTA:** `검토 · 정리 열기` → navigates to Work route, mode `resolve` (not a full table)

**v1:** No persistent shell-bottom `FileDock` with full table. **v2 candidate:** promote strip CTA to persistent dock.

### GlobalCommandBar

Owns: pipeline phase label, percent, cancel, optional **전체 실행** entry (full pipeline subflow).

**Forbidden:** duplicate progress in Work mode headers, stepper inline bars, or section footers.

#### Full-pipeline (“전체 실행”) preflight rules

- **전체 실행** is shown only when it is safe to offer a pipeline run (not while another cancellable run is active unless UI explicitly supports queueing — v1: disabled while running).
- If the user is in **Resolve** mode and there are **unconfirmed destructive previews** (pending move/duplicate apply decisions, open preview without confirm, or `work.resolve` flags `hasPendingApply`), **전체 실행 must not start immediately**. It opens a **preflight subflow** that lists blockers (e.g. N unreviewed rows, M conflicts) and requires explicit confirm or “resolve first” path.
- If no blockers: **전체 실행** opens the normal `SubflowDialog` (scan → duplicate → optional move preview).
- Batch apply from Resolve always uses **SelectionScope** + `getMovePreview` → confirm → `applyResolvedActions`; never bypasses preview.

```text
GlobalCommandBar may expose "전체 실행" only when no unresolved destructive preview is pending.
If review rows contain unconfirmed move/duplicate actions, the button opens a preflight subflow
instead of starting immediately.
```

### Sidebar routes (v1)

| Route | v1 scope |
|-------|----------|
| Work | Full mode-based UI |
| Settings | Shell parity / placeholder acceptable |
| Logs | Shell parity / placeholder acceptable |

---

## Work route — mode tabs

```
WorkRoute
├── WorkModeTabs: [스캔] [검토 · 정리] [품질]
├── ScanWorkspace
├── ResolveAndOrganizeWorkspace   ← primary review surface
└── QualityWorkspace
```

Default mode after scan complete: **resolve**.

`WorkModeTabs` replaces a mandatory `WorkHero` dashboard; orientation only (no stacked summary cards).

---

## Mode 1 — Scan / Import

**Purpose:** index library; **no** full file table.

Components:

- Folder picker (bridge command)
- Scan options summary (chips; link to Settings)
- Scan start / cancel
- Result summary: file count, size, encoding candidates
- CTA: `검토 · 정리로 이동`

**data-state** on scan section per DESIGN.md (`empty`, `running`, `success`, `error`, …).

---

## Mode 2 — Resolve & Organize (core)

**Purpose:** single **decision queue** for keeper, duplicate action, target folder, conflicts — duplicate review and move planning are **one workflow**.

### Layout

```
ResolveAndOrganizeWorkspace
├── Toolbar: search · sort · view mode · dry-run summary chips
├── FacetPanel (left)
├── VirtualizedReviewGrid (center)
├── EvidenceAndMoveDetailPanel (right)
└── BatchActionBar (bottom)
```

### Review view modes (FacetPanel)

| ID | Label | Default | Row unit |
|----|-------|---------|----------|
| `action` | Action Queue | **yes** | Groups/files needing review |
| `groups` | Duplicate Groups | no | Duplicate groups |
| `move` | Move Plan | no | Files with proposed move |
| `all` | All Files | no | File-level (secondary) |
| `conflicts` | Conflicts Only | no | Conflicting items |

**Principle:** default view is **not** raw full-file list; expand group → child files when needed.

### Default grid columns (visible)

| Column | Notes |
|--------|--------|
| Status | 미검토 / 승인 / 충돌 / 제외 |
| Type | exact / near / relation / move-only |
| Name | + keeper subline |
| Proposed action | keep / move duplicate / move organized / ignore |
| Target | folder |
| Confidence | — for move-only |

### Hidden by default (column chooser or detail panel)

Path, Modified, Encoding, Integrity, extended attributes.

### Detail panel (right)

- Keeper decision
- Move plan (action, target)
- Encoding / integrity (read-only in this mode when relevant to conflict)
- Collapsible decision JSON (evidence)

### Batch action bar

- Selection count reflects **`SelectionScope`** (see Bridge contract), not implicit “all rows in memory”
- `선택 승인` / `선택 제외` — commands include `selection: SelectionScope`
- `이동 계획 미리보기` → **Apply subflow** (Dialog: preview → confirm → apply)
- **현재 필터 결과 전체 승인** (if offered): must use `{ type: "current_query", query, excludeRowIds }` never client-side full-library iteration

### User task alignment (NN/g data table tasks)

Grid must support: **find**, **compare**, **single-row detail**, **row-level actions** — not passive listing.

---

## Mode 3 — Quality / Integrity

**Purpose:** readability, encoding, corruption — **not** “where to move file”.

Components (v1):

- Integrity issue list (query-backed; virtualized when large)
- Encoding issue list
- UTF-8 conversion / repair: **read-only + stub actions** (no blocking apply in v1)
- Small-file anomaly: stub or read-only

**Out of v1:** Finalize apply, blocking `QEventLoop`-style sync, full repair pipeline.

---

## Subflows (wizard-only)

| Trigger | UI | Steps |
|---------|-----|--------|
| Full pipeline auto-run | `SubflowDialog` | scan → duplicate → optional move preview; cancel anytime |
| Move / batch apply | `ApplySubflowDialog` | dry-run table → confirm → apply |
| Any destructive apply | Same invariant | preview → confirm → apply |

Progress during subflow runs: **GlobalCommandBar only**.

---

## Bridge & snapshot contract

### Layering

- **Python `application`:** use cases, policies, runners (unchanged responsibility).
- **`NovelGuardBridge` (pywebview `js_api`):** commands + query methods; exposes promises to `window.pywebview.api.*`.
- **React `web/`:** renders snapshots; **no** duplicate-detection or move policy in UI files.

### AppSnapshot (immutable, small)

```typescript
interface PipelineSnapshot {
  phase: string;
  percent: number;
  label: string;
  cancellable: boolean;
}

interface ScanSnapshot {
  state: "empty" | "ready" | "running" | "success" | "error";
  lastRun: string | null;
}

interface ResolveSnapshot {
  queueCount: number;
  groupCount: number;
  conflictCount: number;
  approvedCount: number;
  hasPendingApply: boolean; // true → GlobalCommandBar "전체 실행" uses preflight
}

interface QualitySnapshot {
  integrityIssueCount: number;
  encodingIssueCount: number;
  smallFileAnomalyCount: number;
}

interface AppSnapshot {
  route: "work" | "settings" | "logs";
  theme: "dark" | "light";
  locale: string;
  connection: string;

  library: {
    folderPath: string | null;
    fileCount: number;
    totalBytes: number;
    duplicateGroups: number;
    integrityIssues: number;
    lastRun: string | null;
    scanOptions: string[];
  };

  pipeline: PipelineSnapshot;

  work: {
    activeMode: "scan" | "resolve" | "quality";
    scan: ScanSnapshot;
    resolve: ResolveSnapshot;
    quality: QualitySnapshot;
  };

  fileListSummary: {
    totalCount: number;
    filteredCount: number;
    issueCount: number;
    selectedCount: number;
  };
}
```

**Forbidden:** `fileList: Row[]`, `reviewRows: Row[]`, or any unbounded array in snapshot.

### Query / command API (v1 minimum)

| Method | Kind | Purpose |
|--------|------|---------|
| `selectFolder()` | command | Folder picker |
| `startScan(options?)` | command | Begin scan |
| `cancelRun()` | command | Cancel pipeline |
| `getSnapshot()` | query | Refresh `AppSnapshot` |
| `queryReviewRows(query: ReviewRowsQuery)` | query | Resolve grid page → `ReviewRowsPage` |
| `queryFileRows(query: FileRowsQuery)` | query | All-files view → `FileRowsPage` (same pagination shape as review) |
| `queryQualityRows(query: QualityRowsQuery)` | query | Quality mode grids → `QualityRowsPage` |
| `getDuplicateGroupDetail(groupId)` | query | Resolve detail panel (group) |
| `getQualityIssueDetail(issueId)` | query | Quality detail panel |
| `getMovePreview(selection: SelectionScope)` | query | Subflow preview table |
| `applyResolvedActions(selection: SelectionScope)` | command | After confirm only |
| `setWorkMode(mode)` | command | Optional; or UI-local with snapshot sync |

**Pagination:** cursor + `limit` (default 50–100). UI virtualizes **visible window only** with small overscan.

**Refresh strategy (v1):** poll `getSnapshot()` ~1 Hz while running + on command completion; plan may refine to push events.

### Query DTOs (response shapes)

Implementers must not invent alternate shapes; extend via optional fields only.

#### Review rows (Resolve & Organize)

```typescript
type ReviewViewMode = "action" | "groups" | "move" | "all" | "conflicts";

interface ReviewRowsQuery {
  viewMode: ReviewViewMode;
  filters?: {
    status?: Array<"unreviewed" | "approved" | "conflict" | "excluded">;
    types?: Array<"exact" | "near" | "relation" | "move_only">;
    search?: string;
  };
  sort?: { field: string; direction: "asc" | "desc" };
  cursor?: string | null;
  limit?: number; // default 100, max 200
}

interface ReviewRow {
  id: string;
  rowKind: "group" | "file";
  status: "unreviewed" | "approved" | "conflict" | "excluded";
  type: "exact" | "near" | "relation" | "move_only";
  name: string;
  keeperLabel?: string;
  proposedAction: "keep" | "move_duplicate" | "move_organized" | "ignore";
  targetFolder?: string;
  confidence?: number; // 0–100 when applicable
  sizeBytes?: number;
  encoding?: string;
  integrity?: string;
  hasChildren: boolean;
  groupId?: string; // when rowKind === "file"
}

interface ReviewRowsPage {
  rows: ReviewRow[];
  pageInfo: {
    cursor: string | null;
    nextCursor: string | null;
    hasMore: boolean;
    totalFiltered: number;
  };
  summary: {
    selectedCount: number;
    conflictCount: number;
    unreviewedCount: number;
    approvedCount: number;
  };
}
```

UI maps Korean labels (미검토, 승인, …) from these enums in the presentation layer.

#### Quality rows (Quality mode)

```typescript
type QualityIssueType = "integrity" | "encoding" | "small_file";

interface QualityRowsQuery {
  issueType: QualityIssueType;
  filters?: { search?: string; severity?: "warning" | "error" };
  sort?: { field: string; direction: "asc" | "desc" };
  cursor?: string | null;
  limit?: number;
}

interface QualityRow {
  id: string;
  issueType: QualityIssueType;
  name: string;
  path?: string;
  encoding?: string;
  integrity: string;
  severity: "warning" | "error";
  suggestedAction?: string; // v1 read-only label, not executable repair
}

interface QualityRowsPage {
  rows: QualityRow[];
  pageInfo: ReviewRowsPage["pageInfo"];
  summary: { issueCount: number; warningCount: number; errorCount: number };
}

interface QualityIssueDetail {
  id: string;
  issueType: QualityIssueType;
  name: string;
  path?: string;
  encoding?: string;
  integrity: string;
  evidence?: Record<string, unknown>;
}
```

#### Selection scope (P0.5 — required)

Batch actions and `getMovePreview` / `applyResolvedActions` accept **`SelectionScope`**, not ad-hoc row id arrays alone.

```typescript
type SelectionScope =
  | { type: "explicit_rows"; rowIds: string[] }
  | {
      type: "current_query";
      query: ReviewRowsQuery;
      excludeRowIds: string[];
    };
```

Rules:

- `explicit_rows`: user checkbox selection in the current grid page (may span pages only if UI explicitly accumulates ids).
- `current_query`: “apply to all rows matching this filter” — server resolves ids; `excludeRowIds` removes exceptions.
- Commands reject empty scopes with a typed error.
- UI shows scope label: e.g. `3 selected` vs `412 in current filter (2 excluded)`.

### ViewModel mapping (legacy parity)

Python application DTOs should align with former boundaries where useful:

- `WorkViewModel` / pipeline → `AppSnapshot.pipeline` + `work.*` counts
- Scan → `work.scan`
- Duplicate + Move → **`queryReviewRows` + `getDuplicateGroupDetail`** (merged UI; separate use cases OK underneath)
- Integrity → `work.quality` + **`queryQualityRows` + `getQualityIssueDetail`**

---

## Performance contract

| Rule | Requirement |
|------|-------------|
| DOM rows | Only visible rows + overscan rendered |
| Data | Server-side filter/sort/page; client does not hold full library in memory |
| Snapshot size | O(1) row arrays — counts and summaries only |
| Grid library | **v1 default:** `@tanstack/react-virtual` + `@tanstack/react-table` |

Reference: mock `ReviewGrid` in `Sample/MockUp/MockUp.jsx` (educational only; manual windowing).

### Grid stack decision (v1 default + criteria)

| Criterion | TanStack Virtual + Table | AG Grid Community |
|-----------|--------------------------|-------------------|
| Design freedom (DESIGN.md tokens) | **High** — headless markup/styles | Medium — theming API |
| Built-in features (resize, filter UI) | Compose manually | **Strong** built-ins |
| Bundle / complexity | Low–medium | Medium–high |
| Custom workflow (Action Queue, facets) | **Fits** | Faster for generic data grids |
| **NovelGuard v1** | **Recommended default** | Alternative if team wants fastest column features |

**Decision:** v1 implementation plan uses **TanStack Virtual + TanStack Table**. AG Grid remains an documented alternative if a milestone needs built-in column tooling before custom UI is ready.

---

## Design tokens

- **SSOT:** `DESIGN.md` → `web/src/styles/globals.css` `@theme`
- Mock uses ad-hoc slate/sky palette; **production `web/` must use DESIGN tokens** (`bg-surface`, `text-primary`, …)
- No new hex in feature components

---

## v1 scope

### In

- `web/` scaffold (Vite + React + TS + Tailwind v4 per plan)
- App shell + FileSummaryStrip + GlobalCommandBar
- Work modes: Scan, Resolve & Organize (full workspace), Quality (read-heavy)
- Bridge skeleton + `AppSnapshot` + `queryReviewRows` + `queryQualityRows`
- Virtualized Resolve grid
- Apply subflow (preview → confirm; apply wired to commands)
- Reference alignment with `Sample/MockUp/MockUp.jsx` layout

### Out

- Four-card Work dashboard
- `FileListSheet` as primary review UI
- Full rows in `AppSnapshot`
- Finalize / repair apply, blocking sync loops
- Persistent shell `FileDock` (v2)
- GlobalActionToolbar undo stack
- QSS / objectName registry
- Full i18n sweep (maintain Korean copy list in plan)
- Settings expert mode / structured logs table (P2)

---

## v2 candidates

- Shell-bottom persistent file dock
- Push-based snapshot updates
- Quality workspace full virtualization parity with Resolve
- Column chooser persistence

---

## Open items (implementation plan only)

1. `FileSummaryStrip` CTA: switch to `resolve` mode only vs also restore last `ReviewRowsQuery` / focus selection (default: **mode switch only** in v1).
2. `ResolveSnapshot.hasPendingApply` field naming in `AppSnapshot.work.resolve` (plan defines exact flags for preflight).

---

## Approval checklist

- [x] P0 IA and mode structure approved
- [x] Resolve & Organize merge approved
- [x] Snapshot / query contract approved (incl. `ReviewRowsPage`, `QualityRowsPage`, `SelectionScope`)
- [x] v1 in/out scope approved
- [x] Mock is reference-only; production uses `web/` + DESIGN tokens
- [x] Gate review augmentations (DTOs, selection, quality query, grid criteria, preflight rule)

---

## Changelog

| Date | Change |
|------|--------|
| 2026-06-01 | Initial spec from brainstorming; supersedes 4-card WorkSurface design |
| 2026-06-01 | Gate review: `ReviewRowsPage`/`ReviewRow`, `SelectionScope`, quality queries, grid criteria, GlobalCommandBar preflight; status → approved |
| 2026-06-01 | Fix duplicate `AppSnapshot` TypeScript block (single declaration) |
| 2026-06-01 | PR-10 contract audit: validators + tests; forbidden snapshot arrays enforced |
