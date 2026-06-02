# PR-25: Shell FileDock — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** AppShell-owned persistent **`ShellFileDock`** on all routes, **`FileSummaryStrip` removed**, **`queryFileRows` v1** on bridge (mock + pywebview/Python parity), search + basic/review presets + density, `novelguard.shellFileDock.v1.*` persistence — **no PR-29 advanced grid/backend**.

**Architecture:** `AppSnapshot` aggregates (`library`, `fileListSummary`) for collapsed header → `bridge.queryFileRows` when expanded (cursor + limit, search in query) → dock table reuses review-grid virtualization patterns → no `fileList[]` on snapshot.

**Tech Stack:** React 19 + TypeScript + Vitest (`web/`), Python 3.12 bridge (`src/app/bridge_api.py`, `library_session`) for pywebview parity.

**Spec:** [013-2026-06-02-shell-filedock-design.md](../specs/013-2026-06-02-shell-filedock-design.md) (**approved** 2026-06-02 — LOCK-B1..B5, LOCK-1..10)

**Plan status:** **Approved** (2026-06-02) — Task 1+ implementation in progress

**Prerequisite:** Spec 013 approved; PR-24 merged to `main` (`ac5ad5a` or later includes spec 013 commit)

**Parent:** [001 PR-20..25 roadmap](../roadmap/001-2026-06-02-pr20-pr25-development-roadmap.md)

**Test policy:** Extend `web/src/bridge/bridgeParity.test.ts`, existing Vitest modules under `web/src/` — **no new test files** without `TEST_ALLOWED`. Python: extend `tests/test_bridge_contract.py` if bridge method added.

**Scope freeze:** No packaging changes. No Logs/Settings redesign. No quality-grid virtualization parity. No technical column preset unless trivial after Tasks 1–9. No PR-29 SQLite-scale file index.

---

## Plan-locked constants (spec 013 approved)

| Constant | Value |
|----------|--------|
| Dock owner | `App` + `AppShell` (`fileDock` slot in content column) |
| Routes | `work`, `logs`, `settings` — dock **never unmounts** |
| Default dock state | collapsed |
| Collapsed height | header only ~44–52px |
| Expanded height default | 26–30% viewport |
| Expanded height min / max | 180px / 45% viewport |
| Persistence prefix | `novelguard.shellFileDock.v1.*` |
| Keys | `.expanded`, `.heightPx`, `.density`, `.columnPreset` |
| Search persist | **never** (in-memory during session / route switches only) |
| `queryFileRows` limit default / max | 100 / 200 |
| Required presets | `basic`, `review` |
| Deferred preset | `technical` (optional stretch) |
| Fetch gate | `queryFileRows` only when dock **expanded** |
| PR-29 boundary | Advanced backend, saved search, full 10-col enterprise grid, cross-surface sync |

---

## Slice boundary (B4)

```text
PR-25: queryFileRows v1 (cursor page, mock + Python stub, dock UI)
PR-29: advanced query / DB-backed library grid / shared Work surfaces
```

---

## File map

| File | Action |
|------|--------|
| `web/src/types/fileRows.ts` | **Create** — `FileRowsQuery`, `FileRow`, `FileRowsPage` |
| `web/src/bridge/NovelGuardBridge.ts` | **Modify** — `queryFileRows` |
| `web/src/bridge/mockBridge.ts` | **Modify** — in-memory inventory + `queryFileRows` |
| `web/src/bridge/pywebviewBridge.ts` | **Modify** — `query_file_rows` adapter |
| `web/src/bridge/testBridge.ts` | **Modify** — failure injection hook if needed |
| `web/src/contracts/bridgeParity.ts` | **Modify** — method lists |
| `web/src/bridge/bridgeParity.test.ts` | **Modify** — parity + query cases |
| `web/src/components/layout/ShellFileDock.tsx` | **Create** |
| `web/src/components/layout/shellFileDockStorage.ts` | **Create** |
| `web/src/components/layout/AppShell.tsx` | **Modify** — content column + `fileDock` slot; remove `strip` for summary |
| `web/src/app/App.tsx` | **Modify** — mount `ShellFileDock`, remove `FileSummaryStrip` |
| `web/src/components/layout/FileSummaryStrip.tsx` | **Delete** or keep unused until delete in same PR (prefer delete) |
| `src/app/bridge_api.py` | **Modify** — `query_file_rows` JSON entry |
| `src/app/bridge_parity.py` | **Modify** — export name list |
| `src/application/file_query.py` | **Create** — v1 in-memory/page helper (mirror `review_query.py`) |
| `src/application/library_session.py` | **Modify** — scan cache → `query_file_rows` |
| `tests/test_bridge_contract.py` | **Extend** — `query_file_rows` shape smoke |

**Do not edit in this slice:** `docs/superpowers/README.md`, roadmap files (separate docs commit).

---

## Locked contracts (plan)

### LOCK-P25-1 — AppShell ownership

- `ShellFileDock` is passed into `AppShell` as `fileDock` and rendered **below** route `children` inside the main content column (not under sidebar, not in `GlobalCommandBar`).
- **Forbidden:** route-level dock; Work-only dock; remount on `setRoute`; `FileSummaryStrip` + dock duplicate counts/path.

### LOCK-P25-2 — FileSummaryStrip removed

Collapsed dock header shows: chevron, title, truncated `library.folderPath`, file/dup/integrity chips, **`검토 · 정리 열기`** (same behavior as strip CTA).

### LOCK-P25-3 — `queryFileRows` v1 (aligns spec LOCK-B4)

DTOs follow [000 pagination shape](../specs/000-2026-06-01-novelguard-ui-overhaul-design.md) (same as `ReviewRowsPage.pageInfo`):

```typescript
export type FileRowColumnPreset = "basic" | "review";

export type FileRowDensity = "comfortable" | "compact";

export interface FileRowsQuery {
  search?: string;
  preset?: FileRowColumnPreset;
  cursor?: string | null;
  limit?: number;
}

export interface FileRow {
  id: string;
  name: string;
  path: string;
  sizeBytes?: number;
  modifiedAt?: string;
  extension?: string;
  duplicateGroupId?: string | null;
  isKeeper?: boolean | null;
  integrityStatus?: string | null;
}

export interface FileRowsPage {
  rows: FileRow[];
  pageInfo: {
    cursor: string | null;
    nextCursor: string | null;
    hasMore: boolean;
    totalFiltered: number;
  };
}
```

Rules:

- v1 mock-backed; Python returns same JSON shape from session scan cache (in-memory).
- **Cursor + limit required**; offset pagination only inside helper — not PR-29 DB cursor semantics.
- `limit` clamped to max 200; default 100.
- Search via `FileRowsQuery.search` (case-insensitive name/path/extension) — **no snapshot mutation**.
- **Not in v1:** full-library client fetch; regex/fuzzy; saved searches.

### LOCK-P25-4 — Persistence keys

```text
novelguard.shellFileDock.v1.expanded
novelguard.shellFileDock.v1.heightPx
novelguard.shellFileDock.v1.density
novelguard.shellFileDock.v1.columnPreset
```

Invalid/corrupt values → safe defaults (collapsed, default height %, comfortable, basic). Search **not** stored.

### LOCK-P25-5 — Presets

| Preset | Visible columns |
|--------|-----------------|
| basic | name, path, size, modified |
| review | name, size, duplicateGroup, keeper, integrity |

`technical` — defer unless trivial after Task 9.

---

## Task 0: Plan gate

- [x] Spec 013 **approved** on `main`
- [x] Plan 019 **approved** by human (2026-06-02)
- [x] Branch from `main` after PR-24 merge
- [x] Confirm **no** README/roadmap edits in implementation commits

**Verify:**

```bash
git status
git log --oneline -5
```

---

## Task 1: File row types + bridge interface

**Files:** `web/src/types/fileRows.ts`, `web/src/bridge/NovelGuardBridge.ts`

- [x] Add `FileRowsQuery`, `FileRow`, `FileRowsPage`, preset/density types
- [x] Add `queryFileRows(query: FileRowsQuery): Promise<FileRowsPage>` to `NovelGuardBridge`
- [x] Stub `mockBridge` / `pywebviewBridge`; parity lists updated
- [x] `npm run build` passes

**Suggested commit:** `[pr25] add file rows query contract`

---

## Task 2: `queryFileRows` v1 — mock bridge

**Files:** `web/src/bridge/mockBridge.ts`

- [ ] Seed in-memory file inventory (≥ mock library `fileCount`; stable sort by path)
- [ ] Implement search (name, path, extension), cursor page, `totalFiltered`, `hasMore`
- [ ] Clamp `limit`; empty library → empty page

**Tests (extend existing):** `web/src/bridge/bridgeParity.test.ts` or colocated `mockBridge` test module if one exists — filter, case-insensitive, limit clamp, cursor advance

**Suggested commit:** `[pr25] implement queryFileRows v1 mock`

---

## Task 3: `queryFileRows` — pywebview + Python parity

**Files:** `pywebviewBridge.ts`, `bridge_api.py`, `bridge_parity.py`, `file_query.py`, `library_session.py`, `tests/test_bridge_contract.py`

- [ ] `query_file_rows` / `query_file_rows_json` on API
- [ ] Session serves pages from scan cache (v1 in-memory; OK if stub until scan populates)
- [ ] `bridgeParity.ts` + `PYWEBVIEW_API_METHODS` include `queryFileRows` / `query_file_rows`
- [ ] Contract test: minimal shape keys

**Suggested commit:** `[pr25] add queryFileRows bridge parity`

---

## Task 4: `shellFileDockStorage` + defaults

**Files:** `web/src/components/layout/shellFileDockStorage.ts`

- [ ] read/write helpers for LOCK-P25-4 keys
- [ ] try/catch around `localStorage`; corrupt → defaults
- [ ] Unit tests in existing vitest file or `shellFileDockStorage.test.ts` only if `TEST_ALLOWED`

**Suggested commit:** `[pr25] persist shell file dock state`

---

## Task 5: `ShellFileDock` component

**Files:** `web/src/components/layout/ShellFileDock.tsx`

- [ ] States: collapsed, expanded, empty, filtered
- [ ] Collapsed: header summary (LOCK-P25-2); no table repaint
- [ ] Expanded: search, preset, density, table; calls `queryFileRows` only when expanded
- [ ] Debounce search ≥ 200ms; pass `search` in query
- [ ] Windowed/virtualized table (reuse patterns from `ResolveAndOrganizeWorkspace` — do not fork unrelated grid)
- [ ] Height resize within LOCK-6 clamp

**Suggested commit:** `[pr25] add shell file dock component`

---

## Task 6: Replace `FileSummaryStrip`

**Files:** `App.tsx`, `FileSummaryStrip.tsx`, `AppShell.tsx`

- [ ] Remove `strip={<FileSummaryStrip .../>}` usage
- [ ] Delete `FileSummaryStrip.tsx` if fully replaced
- [ ] Wire `onOpenResolve` into dock header CTA
- [ ] **No** duplicate summary row above dock

**Suggested commit:** `[pr25] replace file summary strip with dock header`

---

## Task 7: Mount dock in `AppShell` (all routes)

**Files:** `AppShell.tsx`, `App.tsx`

- [ ] Add `fileDock?: ReactNode`; layout: `children` flex-1, `fileDock` shrink-0 inside `<main>`
- [ ] `App` passes `<ShellFileDock ... />` — **outside** route `switch`, same instance across routes
- [ ] Route switch preserves expanded / heightPx / preset / density / in-memory search
- [ ] Logs/Settings remain usable when dock expanded (max height enforced)

**Suggested commit:** `[pr25] mount shell file dock in app shell`

---

## Task 8: Presets + density

**Files:** `ShellFileDock.tsx`

- [ ] Column visibility per LOCK-P25-5
- [ ] Density toggles row spacing / typography classes
- [ ] Persist preset + density via storage helper

**Suggested commit:** `[pr25] add file dock presets and density`

---

## Task 9: Tests + bridge parity closure

**Extend only (no new files without approval):**

- [ ] `bridgeParity.test.ts` — `queryFileRows` happy path
- [ ] AppShell/dock tests: strip absent; dock mounted; route switch does not reset expanded (vitest + Testing Library)
- [ ] Mock query: name/path filter, limit, cursor

**Verify:**

```bash
cd web && npm run test
cd web && npm run build
```

**Suggested commit:** `[pr25] cover shell file dock behavior`

---

## Task 10: Final verification

- [ ] `python scripts/verify_phase_completion.py`
- [ ] `cd web && npm run test && npm run build && npm run lint`
- [ ] Manual smoke: work → logs → work — dock collapsed state preserved; expand → search → preset
- [ ] Confirm no `fileList` on snapshot; no PR-29-only backend features

**Suggested commit:** `[pr25] finalize shell filedock implementation`

---

## Task 11: Documentation follow-up (separate commit)

**Not part of implementation PR slice:**

```text
[docs] update roadmap after pr25
```

Files (typical):

- `docs/superpowers/README.md`
- `docs/superpowers/roadmap/001-2026-06-02-pr20-pr25-development-roadmap.md`

---

## Risk register

| Risk | Mitigation |
|------|------------|
| Duplicate summary UI | Remove strip; single collapsed header (LOCK-P25-2) |
| Dock remount on route change | `fileDock` sibling of route children in `App` |
| PR-25 → PR-29 scope creep | Cursor page only; no DB index / saved search |
| Stale search on restart | Do not persist search (LOCK-P25-4) |
| Corrupt `localStorage` | Validated storage helper |
| 1k+ row lag | expand-gated fetch; limit 100; debounce; virtual window |
| Snapshot bloat | Forbidden arrays — use `queryFileRows` only |
| Python/mock drift | `bridgeParity` + contract test |

---

## Done criteria

PR-25 implementation complete when:

- [ ] Plan 019 approved and all tasks checked
- [ ] `ShellFileDock` AppShell-owned; visible on all routes; no remount on route change
- [ ] `FileSummaryStrip` not in layout
- [ ] `queryFileRows` v1 on mock + pywebview/Python
- [ ] Search + basic/review presets + density work
- [ ] `novelguard.shellFileDock.v1.*` persistence (not search)
- [ ] `verify_phase_completion.py` PASS
- [ ] Scope freeze respected

---

## Approval

| Field | Value |
|-------|-------|
| Approved by | Human |
| Date | 2026-06-02 |

**Next:** Task 1 — File row types + bridge interface
