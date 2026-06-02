---
title: PR-25 Shell FileDock
status: approved
grill_me: 2026-06-02
approved: 2026-06-02
date: 2026-06-02
authors: PR-25 spec lead + codebase baseline
parent_spec: docs/superpowers/specs/000-2026-06-01-novelguard-ui-overhaul-design.md
related_specs:
  - docs/superpowers/specs/012-2026-06-02-packaging-distribution-design.md
  - docs/superpowers/specs/011-2026-06-02-finalize-cleanup-pipeline-design.md
roadmap: docs/superpowers/roadmap/001-2026-06-02-pr20-pr25-development-roadmap.md
pr_label: PR-25
plan: docs/superpowers/plans/019-2026-06-02-pr25-shell-filedock.md
prerequisite: PR-24 packaging complete; PR-23 finalize UX stable
---

# 013 — Shell FileDock Design

## Status

**Approved** (2026-06-02) — grill-me **B1–B5** + **LOCK-B1..B5** + G1–G10 locked below. Implementation per plan 019 (not written).

## Scope sentence

PR-25 is **not** a table polish pass. It is **ownership migration**: persistent shell-level `ShellFileDock` owned by the app frame (`App` / `AppShell`), replacing `FileSummaryStrip` + any Work-only file surfaces, with v2 UX (search, column presets, density, height contract). Data: **`AppSnapshot` aggregates** (`library`, `fileListSummary`) plus **new bridge `queryFileRows` v1** (paginated read for dock table only). **PR-29** remains the advanced library-wide grid/backend track — not duplicated in PR-25.

---

## 1. Problem

현재 파일 목록은 Work 탭·워크스페이스 내부(또는 summary-only strip)에 묶여 있다. [000 UI overhaul](000-2026-06-01-novelguard-ui-overhaul-design.md) v1은 shell-bottom full table FileDock을 비목표로 두었고, `FileSummaryStrip` + Work-owned review grid가 canonical이다. 이 구조는 Work에서는 유효하지만, 앱 전체 IA 기준에서는 다음 문제가 있다.

1. 파일 목록이 Work content에 묶여 shell-level persistent surface가 아니다.
2. Logs / Settings 라우트 전환 시 dock 상태와 시각적 연속성이 약하다.
3. 전체 파일 테이블(10컬럼급 밀도)은 유용하지만, 좁은 높이와 가로 스크롤 때문에 밀도·가독성 문제가 있다.
4. Per-file dock rows cannot live on `AppSnapshot` (contract forbids unbounded arrays); a **paginated** bridge read is required.
5. PR-25는 전체 IA 개편이 아니라 FileDock **소유권 이전**과 v2 UX 개선만 다룬다.

```text
Before: Work route / workspace owns full file list UX
After : AppShell / App frame owns ShellFileDock
```

---

## 2. Goals

PR-25의 목표는 다음이다.

- `AppShell` content column 하단에 persistent `ShellFileDock`을 둔다.
- Work 전용 dock·중복 surface는 제거하거나 thin adapter로 전환한다.
- 라우트(work / logs / settings) 전환 시 dock expanded/collapsed, height, density, column preset, search text 정책을 명확히 유지한다.
- `SnapshotProvider` / `getSnapshot()` aggregates unchanged (`library`, `fileListSummary`).
- Add bridge **`queryFileRows` v1** (paginated; dock columns only) on mock + pywebview parity — see **LOCK-B4**.
- `FileRowsProvider` seam wraps `queryFileRows`; PR-29 may replace backend without dock UI rewrite.
- 1k+ file rows에서 UI freeze나 과도한 repaint를 만들지 않는다.

---

## 3. Non-goals

다음은 PR-25 범위 밖이다.

- PR-29 **advanced** library-wide grid (DB index at scale, cross-surface sync, features beyond dock v1)
- Quality grid 가상화 동등 구현
- 전체 Work IA를 단일 scroll work-hub로 변경
- Duplicate / Quality / Logs 테이블 전면 재작성
- Undo/Redo stack 활성화
- Packaging / release artifact 변경 (PR-24 범위)
- PR-26 push snapshot, PR-27 quality virtualization

---

## 4. Current State

### 4.1 Codebase baseline (2026-06-02)

| Layer | Today |
|-------|--------|
| Shell | `web/src/components/layout/AppShell.tsx` — header, sidebar, `children` (main), `strip`, `commandBar` |
| App root | `web/src/app/App.tsx` — route `work` \| `settings` \| `logs`; `FileSummaryStrip` on `strip` slot |
| Work | `WorkRoute` + mode workspaces; review grid in `ResolveAndOrganizeWorkspace` (virtualized, query-shaped rows via snapshot) |
| File dock module | **Not implemented** — no `WorkFileDock` / `ShellFileDock` file yet |
| Persistence | `localStorage` for some grid sizing keys; no `ui/shell_file_dock_*` keys yet |
| Packaging | PR-24 locks no FileDock IA change |

[DESIGN.md](../../../DESIGN.md) sketches `FileDock` inside `WorkSurface`; [000](000-2026-06-01-novelguard-ui-overhaul-design.md) v1 defers persistent shell-bottom full table to v2 (PR-25).

### 4.2 Target mental model (migration)

Legacy/product docs may refer to `WorkTab` / `WorkFileDock` / `QSettings`. PR-25 maps them as:

| Legacy / doc term | PR-25 React target |
|-------------------|---------------------|
| `MainWindow` | `App` + `AppShell` |
| `contentArea` | `AppShell` `children` (route main) |
| `WorkFileDock` | Remove from Work layout; logic → `ShellFileDock` |
| `QSettings` | `localStorage` keys `ui/shell_file_dock_*` (or bridge-backed settings if added later) |
| `FileDataStore` (doc legacy) | **Not in repo** — use `library` + `fileListSummary` + `queryFileRows` |

**Bridge reality (2026-06-02):** `NovelGuardBridge` has `queryReviewRows` / `queryQualityRows` but **no** `queryFileRows` yet. [000](000-2026-06-01-novelguard-ui-overhaul-design.md) documents `queryFileRows` as a v1 API shape; implementation was deferred to PR-29 label — **PR-25 unblocks dock by shipping v1**.

---

## Locked decisions (grill-me — 2026-06-02)

| # | Topic | Lock | Evidence / rationale |
|---|--------|------|----------------------|
| **B1** | `FileSummaryStrip` vs `ShellFileDock` | **Replace** — remove strip slot; collapsed dock header absorbs folder path, aggregate chips, `검토 · 정리 열기` CTA | **Approved 2026-06-02** |
| **B2** | Dock visibility | **All routes** (`work`, `logs`, `settings`) in content column; state survives route switch | **Approved 2026-06-02** |
| **B3** | `localStorage` keys | Namespace **`novelguard.shellFileDock.v1.*`**; legacy `ui/*` keys — ignore | **Approved 2026-06-02** |
| **B4** | Data source of truth | Aggregates: `library` + `fileListSummary`; rows: **`queryFileRows` v1**; PR-29 = advanced only | **Approved 2026-06-02** |
| **B5** | Scope creep | PR-25 ships basic+review preset, density, search; technical preset defer OK in plan 019 | **Approved 2026-06-02** |

### LOCK-B1 — FileSummaryStrip replaced by collapsed dock header

- **Remove** `AppShell` `strip` slot usage for `FileSummaryStrip` in PR-25.
- **Collapsed `ShellFileDock` header** shows: chevron, label, folder path (truncated), file/dup/integrity chips, `검토 · 정리 열기`.
- **Expanded** adds search, preset, density, table (no second summary row).
- **Forbidden:** strip + dock both showing file totals or folder path.

### LOCK-B2 — Dock visible on every route

- Mount `ShellFileDock` under content column for **all** routes; do not unmount on `logs` / `settings`.
- Default **collapsed** globally (including first visit).
- Expanded dock on Logs/Settings must still respect LOCK-6 max height (content remains usable).

### LOCK-B3 — Persistence keys

| Key | Meaning |
| --- | --- |
| `novelguard.shellFileDock.v1.expanded` | `"true"` \| `"false"` |
| `novelguard.shellFileDock.v1.heightPx` | expanded height px |
| `novelguard.shellFileDock.v1.density` | `comfortable` \| `compact` |
| `novelguard.shellFileDock.v1.columnPreset` | `basic` \| `review` \| `technical` |

- **Do not persist** search text across restart (in-memory only during session / route switches).
- Legacy `ui/work_file_dock_*` / `ui/shell_file_dock_*`: **ignore** (never shipped).

### LOCK-B4 — `queryFileRows` v1 in PR-25 (not PR-29)

PR-25 **must** add to `NovelGuardBridge`:

```typescript
queryFileRows(query: FileRowsQuery): Promise<FileRowsPage>;
```

**v1 constraints (dock-only):**

- Cursor pagination (`limit` default 100, max 200).
- Columns map to LOCK-8 presets (server/mock may return superset; UI filters columns).
- Search/filter in UI applies to **fetched page** or passes `search` in query if bridge supports — prefer **query param** to avoid loading 1k rows client-side.
- Mock + pywebview parity required for `verify_phase_completion` / e2e.
- **Snapshot contract unchanged** — no `fileList` on `AppSnapshot`.

**PR-29** (still out of scope): library DB index at scale, shared grid with Work surfaces, saved searches, advanced filters, parity with full 10-column enterprise grid.

**Subscriptions:** single `SnapshotProvider` context; dock calls `queryFileRows` when **expanded** (and on snapshot revision bump for counts when collapsed). **Forbidden:** second snapshot poller or duplicate `getSnapshot` loop for dock only.

### LOCK-B5 — PR-25 slice boundary

| Ship in PR-25 | Defer (plan 019 task or PR-29) |
|---------------|--------------------------------|
| Shell ownership, AppShell layout, strip removal | Technical column preset (if slip) |
| Collapsed default, height min/max | Regex / fuzzy search |
| `queryFileRows` v1 + virtualized/paginated table | Full-library client-side load |
| Search filename/path/extension | `queryFileRows` backend on SQLite at scale |
| Presets basic + review, density toggle | Optional header filters (LOCK-7 optional) |

---

## 5. Design Decision Locks

### LOCK-1 — Shell owns FileDock

`ShellFileDock`의 소유자는 app frame (`App` / `AppShell`)이다.

금지:

- `WorkRoute`가 새 dock 인스턴스를 직접 소유
- Logs/Settings가 dock lifecycle에 개입
- 라우트마다 dock를 재생성

허용:

- Work workspaces는 scan/file events를 기존처럼 snapshot·bridge에 반영
- `ShellFileDock`은 store/snapshot을 구독·refresh

---

### LOCK-2 — Dock location

`ShellFileDock`은 AppShell의 main content column 하단에 위치한다.

권장 구조:

```text
App
├── AppHeader
├── GlobalCommandBar (existing slot — do not duplicate progress)
└── MainBody
    ├── AppSidebar
    └── ContentColumn
        ├── Route main (WorkRoute | PlaceholderRoute …)
        └── ShellFileDock
```

Sidebar 아래까지 dock을 full-width로 깔지 않는다.  
이유: nav 영역과 data dock의 책임을 분리하고, 하단 dock이 sidebar navigation을 먹지 않게 한다.

**FileSummaryStrip:** removed in PR-25 — see **LOCK-B1**. Full table lives only in expanded `ShellFileDock`.

---

### LOCK-3 — Work dock removal

Work layout 내부의 file dock·splitter·전용 file table surface는 제거한다.

허용되는 migration 방식:

1. 신규 `ShellFileDock` 컴포넌트; Work에서 file table 제거
2. 공통 table primitive 추출 후 owner만 shell로 이동

금지:

- Work 내부 dock + Shell dock 동시 표시
- 동일 file index를 두 surface가 동시에 heavy-subscribe 해 중복 repaint 발생

---

### LOCK-4 — Data layers (aligns with LOCK-B4)

| Layer | Source | Use |
|-------|--------|-----|
| Aggregates | `AppSnapshot.library`, `fileListSummary` | Collapsed header chips, empty state |
| Row pages | `bridge.queryFileRows(query)` | Expanded table only |
| Review grid | `queryReviewRows` (unchanged) | Resolve workspace — **not** dock data |

`FileRowsProvider` (TS) wraps `queryFileRows` + snapshot revision for refresh; plan 019 locks DTOs to [000 `FileRowsQuery` / `FileRowsPage`](000-2026-06-01-novelguard-ui-overhaul-design.md) shape.

**Forbidden:** `fileList[]` on snapshot; naming a Python `FileDataStore` in PR-25 without a spec/plan task.

---

### LOCK-5 — Dock persistence

See **LOCK-B3** for keys (`novelguard.shellFileDock.v1.*`). Search: in-memory only across route switches; **not** in `localStorage`.

---

### LOCK-6 — Height contract

Dock은 다음 height contract를 따른다.

| State | Height |
| --- | --- |
| collapsed | header only, 약 44–52px |
| expanded default | viewport height의 26–30% |
| expanded min | 180px |
| expanded max | viewport height의 45% |

Dock이 expanded되어도 Work/Logs/Settings content의 minimum usable height를 침범하지 않는다.

---

### LOCK-7 — Header UX

ShellFileDock header는 다음 요소를 가진다.

```text
[chevron] 파일 목록 [count chip] [filtered count chip?]
[search input] [column preset] [density toggle] [open/close]
```

필수:

- 파일 총수
- 검색어 존재 시 filtered count
- collapsed 상태에서도 파일 수는 보여야 함
- 검색은 filename/path 중심

선택:

- extension filter
- issue-only filter
- duplicate-only filter

---

### LOCK-8 — Column presets

PR-25는 컬럼 개별 show/hide editor가 아니라 preset까지만 제공한다.

| Preset | Columns |
| --- | --- |
| Basic | 파일명, 경로, 크기, 수정일 |
| Review | 파일명, 크기, 중복 그룹, 대표 파일, 무결성 |
| Technical | 파일명, 경로, 확장자, 인코딩, 속성, 수정일 |

기존 10컬럼급 정보는 Technical preset에서 대부분 접근 가능해야 한다.

---

### LOCK-9 — Performance floor

1k+ rows 기준 다음을 지킨다.

- search 입력 debounce 적용
- 전체 테이블 rebuild 남발 금지
- batch update path 유지
- 라우트 전환만으로 row model recreate 금지
- expanded/collapsed toggle이 **full** `queryFileRows` refetch를 유발하지 않아야 함 (cache page in dock state; refetch on `libraryRevision` / scan complete only)
- **`queryFileRows` only when expanded** (collapsed = header counts from snapshot only)

PR-25: reuse review-grid **virtualization pattern** for visible window; paginated fetch — **no** client-side load of full library. Debounce search ≥ 200ms.

---

### LOCK-10 — Work pipeline behavior unchanged

FileDock 이동은 pipeline semantics를 바꾸지 않는다.

금지:

- scan/deduplicate/move/finalize command 위치 변경
- pipeline runner 순서 변경
- `GlobalCommandBar` progress 정책 변경
- Duplicate/Move/Finalize apply behavior 변경

허용:

- Work layout에서 dock/splitter 제거로 인한 vertical space 재배치
- Work tab layout regression tests (existing suite / e2e where applicable)

---

## 6. UI Contract

### 6.1 Collapsed

Collapsed 상태:

```text
▸ 파일 목록   1,248 files   23 issues   Search hidden/compact
```

- 높이는 header only
- table hidden
- count updates still visible
- expensive table repaint 없음

### 6.2 Expanded

Expanded 상태:

```text
▾ 파일 목록   1,248 files   Showing 312
[Search files...] [Preset: Review] [Density: Compact]
----------------------------------------------------
table
```

### 6.3 Empty state

No folder / no scan state:

```text
파일 목록
스캔된 파일이 없습니다. 작업 탭에서 폴더를 선택하고 스캔하세요.
```

### 6.4 Search

Search applies to:

- filename
- relative path
- extension

Not required in PR-25:

- regex
- fuzzy search
- query language
- saved searches

Search **must not** mutate canonical file index / store rows (filter is view-layer only).

---

## 7. Implementation Sketch

### 7.1 Candidate files (React — primary)

```text
web/src/components/layout/AppShell.tsx      # optional: dock slot vs inline in App
web/src/app/App.tsx                         # wire ShellFileDock, persistence restore
web/src/components/layout/ShellFileDock.tsx # new
web/src/components/layout/FileSummaryStrip.tsx  # remove usage (delete or deprecate in PR-25)
web/src/types/fileRows.ts                       # FileRowsQuery / FileRowsPage (plan 019)
web/src/bridge/NovelGuardBridge.ts              # + queryFileRows
web/src/features/work/WorkRoute.tsx         # remove work-internal file dock
web/src/lib/fileRowsProvider.ts             # optional FileRowsProvider seam
```

Reuse patterns from `ResolveAndOrganizeWorkspace` virtualization/table primitives where applicable; do not fork a second unrelated grid stack without plan approval.

### 7.2 App wiring

`App` / `AppShell` should:

1. create `ShellFileDock`
2. connect file rows provider (snapshot / scan index)
3. place dock under route `children` inside content column
4. restore `localStorage` state on mount
5. persist state on close / toggle / resize

### 7.3 Work cleanup

Work route should:

1. remove any work-internal file dock / splitter reserved for file table
2. drop or migrate `ui/work_file_dock_*` keys once
3. keep wizard/mode tabs/footer layout stable
4. keep summary chips / mode workspaces unchanged in pipeline semantics

---

## 8. Tests

Required tests (plan 019 assigns pytest vs vitest vs e2e per file touched):

### Web unit / integration

- `ShellFileDock` is mounted from `App` / shell frame.
- Work route no longer mounts a visible work-only file dock.
- Dock expanded state survives route switch (work → logs → work).
- Dock collapsed state survives route switch.
- Dock height is clamped to min/max.
- File index batch updates refresh dock count.
- Search filters rows without mutating canonical store.
- Column preset changes visible columns.
- Density setting changes row height or table spacing.

### Regression

- Work route still shows mode tabs / workspaces / footer after dock removal.
- Logs and Settings routes remain usable with dock collapsed and expanded.
- Pipeline run still updates file list after scan.
- `python scripts/verify_phase_completion.py` PASS.
- `cd web && npm run test` PASS if web layer touched.
- Existing pytest suite PASS.

**Test file creation:** requires explicit user `TEST_ALLOWED` per [AGENTS.md](../../../AGENTS.md).

---

## 9. Acceptance Criteria

PR-25 is complete when:

1. FileDock visible from Shell/App frame on **all routes**, not Work-only.
2. Dock UI state persists during route switching (`novelguard.shellFileDock.v1.*`).
3. Default state is collapsed.
4. Expanded height obeys min/max contract.
5. Search works for filename/path/extension (debounced; no snapshot mutation).
6. Column presets **basic** and **review** work; density toggle works.
7. Aggregates from snapshot; row pages from `queryFileRows` v1 (mock + pywebview).
8. PR-29 **advanced** grid/backend not implemented; no `fileList` on snapshot.
9. `FileSummaryStrip` removed; collapsed dock shows former strip content.
10. `bridgeParity` / contract tests cover `queryFileRows`.
11. Full verification passes.

---

## 10. Grill-me resolutions (2026-06-02)

| # | Question | Resolution |
|---|----------|------------|
| G1 | Duplicate store subscriptions? | **No** — one `SnapshotProvider`; dock uses snapshot for counts, `queryFileRows` when expanded only (**LOCK-B4**) |
| G2 | Work layout regression? | No Work-internal dock today; removing strip **frees** vertical space — regression: mode tabs + workspaces + `GlobalCommandBar` |
| G3 | Logs/Settings unusable when expanded? | **LOCK-B2** + **LOCK-6** max 45% viewport; test in acceptance |
| G4 | Search mutates canonical data? | **View/query only** — filter via `FileRowsQuery.search` or client filter on page; never mutate snapshot |
| G5 | Preset hides review signals? | Dock presets ≠ Resolve grid columns; review grid unchanged |
| G6 | Stale search on restart? | **No persist** — LOCK-B3 |
| G7 | 1k+ row stalls? | Pagination + debounce + expand-gated fetch — LOCK-9 |
| G8 | PR-29 early? | **v1 `queryFileRows` in PR-25**; PR-29 = advanced backend/grid — LOCK-B4 |
| G9 | Old keys? | **Ignore** `ui/work_file_dock_*` (never shipped) |
| G10 | Packaging? | PR-24 bundles `web/dist` — new components auto-included; no spec change to PR-24 |

---

## 11. References

- [000 UI overhaul](000-2026-06-01-novelguard-ui-overhaul-design.md) — v1 strip + Work grid; v2 FileDock
- [012 Packaging](012-2026-06-02-packaging-distribution-design.md) — LOCK-9: PR-25 out of PR-24 scope
- [Roadmap PR-20..25](../roadmap/001-2026-06-02-pr20-pr25-development-roadmap.md)
- [DESIGN.md](../../../DESIGN.md) — tokens, FileDock placement sketch
