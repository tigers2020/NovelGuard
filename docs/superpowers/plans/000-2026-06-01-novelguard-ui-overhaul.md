# NovelGuard UI Overhaul — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver v1 Hybrid mode-based React UI (`web/`) with query-backed virtualized Resolve workspace, bridge-ready DTOs, and pywebview integration path — per [approved spec](../specs/2026-06-01-novelguard-ui-overhaul-design.md).

**Architecture:** Python `application` owns business logic; `NovelGuardBridge` (pywebview `js_api`) exposes commands/queries; React consumes `AppSnapshot` summaries plus paginated `queryReviewRows` / `queryQualityRows`. UI copies layout intent from `Sample/MockUp/MockUp.jsx` but uses `DESIGN.md` tokens in `web/src/styles/globals.css`.

**Tech Stack:** Vite, React 19, TypeScript, Tailwind CSS v4 (`@tailwindcss/vite`), `@tanstack/react-table`, `@tanstack/react-virtual`, pywebview (host in `src/app/` — plan PR-9).

**Spec:** [2026-06-01-novelguard-ui-overhaul-design.md](../specs/2026-06-01-novelguard-ui-overhaul-design.md) (approved)

## Implementation status

| PR | Status | Branch |
|----|--------|--------|
| PR-0 … PR-9 | **Done** | `feat/web-ui-overhaul` |
| PR-10 | **Done** | see `001-2026-06-01-novelguard-ui-contract-hardening.md` |
| PR-11 | **Done** | see `002-2026-06-01-novelguard-ui-e2e-smoke.md` |
| PR-12 | **Done** | see `003-2026-06-01-novelguard-ui-grid-perf.md` |

**Verification (2026-06-01):** `cd web && npm run build` PASS · `npm run test:contracts` · `npm run test:perf` · `npm run test:e2e` 9/9 · `python scripts/verify_phase_completion.py` PASS

**Run:** `run.bat` (desktop) · `cd web && npm run dev` (browser mock) · E2E: `cd web && npm run test:e2e` · Perf: `cd web && npm run test:perf`

Plan scope freeze holds — PR-13..14 require new spec/plan cycle.

**Test policy:** Do not add new `tests/**` files unless user says `TEST_ALLOWED`. Verify with `npm run lint`, `npm run build`, manual smoke, and `python scripts/verify_phase_completion.py` (includes lint) when Python files change.

---

## File structure (target)

```text
web/
├── index.html
├── package.json
├── vite.config.ts
├── tsconfig.json
├── tsconfig.app.json
└── src/
    ├── main.tsx
    ├── app/
    │   ├── App.tsx
    │   └── providers/SnapshotProvider.tsx
    ├── styles/
    │   └── globals.css              # @import "tailwindcss" + @theme from DESIGN.md
    ├── types/
    │   ├── snapshot.ts              # AppSnapshot, *Snapshot
    │   ├── review.ts                # ReviewRow, ReviewRowsPage, ReviewRowsQuery
    │   ├── quality.ts               # QualityRow, QualityRowsPage, QualityRowsQuery
    │   └── selection.ts             # SelectionScope
    ├── bridge/
    │   ├── NovelGuardBridge.ts      # interface
    │   ├── mockBridge.ts            # PR-1..8 dev adapter
    │   └── pywebviewBridge.ts       # PR-9 window.pywebview.api wrapper
    ├── components/
    │   ├── ui/                      # Button, Card, StatChip, IconButton, Dialog, Sheet
    │   └── layout/
    │       ├── AppShell.tsx
    │       ├── AppHeader.tsx
    │       ├── AppSidebar.tsx
    │       ├── FileSummaryStrip.tsx
    │       └── GlobalCommandBar.tsx
    └── features/
        └── work/
            ├── WorkRoute.tsx
            ├── WorkModeTabs.tsx
            ├── ScanWorkspace.tsx
            ├── ResolveAndOrganizeWorkspace.tsx
            ├── QualityWorkspace.tsx
            ├── ApplySubflowDialog.tsx
            ├── PreflightPipelineDialog.tsx
            ├── resolve/
            │   ├── FacetPanel.tsx
            │   ├── VirtualizedReviewGrid.tsx
            │   ├── DetailPanel.tsx
            │   └── BatchActionBar.tsx
            └── quality/
                └── QualityIssueGrid.tsx

src/app/                               # PR-9 Python host (minimal)
    └── webview_main.py                # pywebview + js_api stub

Sample/MockUp/MockUp.jsx               # reference only — do not import in web/
```

---

## PR map (merge order)

| PR | Scope | Done when |
|----|--------|-----------|
| PR-0 | Vite + React + TS + Tailwind v4 + tokens | `npm run build` passes |
| PR-1 | `types/*` + `mockBridge.ts` | types compile; mock returns spec-shaped JSON |
| PR-2 | App shell layout | Shell renders 3 routes placeholder |
| PR-3 | Scan workspace | Scan mode matches spec (no file table) |
| PR-4 | Resolve skeleton | 3-column layout empty states |
| PR-5 | Virtualized grid + `queryReviewRows` | 1000+ rows scroll smoothly |
| PR-6 | Detail + SelectionScope + batch bar | selection labels + mock preview command |
| PR-7 | Apply + preflight subflows | destructive path preview→confirm only |
| PR-8 | Quality workspace | `queryQualityRows` grid read-only |
| PR-9 | pywebview smoke | `python src/app/webview_main.py` opens UI |

**Plan scope freeze:** Complete PR-0..PR-9 only. No v2 shell FileDock, no Finalize apply, no new test files without `TEST_ALLOWED`.

---

## PR-0: web scaffold + Tailwind token bridge

**Files:**
- Create: `web/package.json`, `web/vite.config.ts`, `web/tsconfig.json`, `web/tsconfig.app.json`, `web/index.html`
- Create: `web/src/main.tsx`, `web/src/app/App.tsx`, `web/src/styles/globals.css`

- [ ] **Step 1: Scaffold Vite React TS**

```bash
cd f:/Python_Projects/NovelGuard
npm create vite@latest web -- --template react-ts
cd web
npm install
npm install -D @tailwindcss/vite tailwindcss
npm install @tanstack/react-table @tanstack/react-virtual
```

- [ ] **Step 2: Configure Tailwind v4 in `web/vite.config.ts`**

```typescript
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: { port: 5173 },
  build: { outDir: "dist" },
});
```

- [ ] **Step 3: Copy `@theme` block from DESIGN.md into `web/src/styles/globals.css`**

```css
@import "tailwindcss";

@theme {
  --color-background: #121212;
  --color-surface: #1e1e1e;
  --color-surface-elevated: #242424;
  --color-on-surface: #eaeaea;
  --color-on-surface-variant: #bdbdbd;
  --color-muted: #8a8a8a;
  --color-primary: #bb86fc;
  --color-secondary: #81d4fa;
  --color-outline: #2c2c2c;
  --color-hover: #2a2a2a;
  --color-error: #cf6679;
  --color-success: #80cbc4;
  --font-family-sans: "Pretendard", "Noto Sans KR", "Segoe UI", sans-serif;
}
```

Import in `main.tsx`: `import "./styles/globals.css";`

- [ ] **Step 4: Minimal `App.tsx` smoke**

```tsx
export default function App() {
  return (
    <div className="min-h-screen bg-background text-on-surface p-6">
      <h1 className="text-xl font-semibold text-primary">NovelGuard</h1>
      <p className="text-on-surface-variant">web scaffold</p>
    </div>
  );
}
```

- [ ] **Step 5: Verify**

```bash
cd web && npm run build
```

Expected: exit 0, `web/dist/` created.

- [ ] **Step 6: Commit** `[web] scaffold Vite React Tailwind v4`

---

## PR-1: DTO types + bridge mock adapter

**Files:**
- Create: `web/src/types/snapshot.ts`, `review.ts`, `quality.ts`, `selection.ts`
- Create: `web/src/bridge/NovelGuardBridge.ts`, `web/src/bridge/mockBridge.ts`
- Create: `web/src/app/providers/SnapshotProvider.tsx`

- [ ] **Step 1: Port interfaces from spec into `web/src/types/`**

`web/src/types/snapshot.ts` — single `AppSnapshot` (no duplicate interfaces):

```typescript
export interface PipelineSnapshot {
  phase: string;
  percent: number;
  label: string;
  cancellable: boolean;
}

export interface ScanSnapshot {
  state: "empty" | "ready" | "running" | "success" | "error";
  lastRun: string | null;
}

export interface ResolveSnapshot {
  queueCount: number;
  groupCount: number;
  conflictCount: number;
  approvedCount: number;
  hasPendingApply: boolean;
}

export interface QualitySnapshot {
  integrityIssueCount: number;
  encodingIssueCount: number;
  smallFileAnomalyCount: number;
}

export interface AppSnapshot {
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

Copy `ReviewRow`, `ReviewRowsPage`, `ReviewRowsQuery`, `QualityRow`, `QualityRowsPage`, `QualityRowsQuery`, `QualityIssueDetail`, `SelectionScope` from spec § Query DTOs into `review.ts`, `quality.ts`, `selection.ts`.

- [ ] **Step 2: Define `NovelGuardBridge` interface**

`web/src/bridge/NovelGuardBridge.ts`:

```typescript
import type { AppSnapshot } from "../types/snapshot";
import type { ReviewRowsPage, ReviewRowsQuery } from "../types/review";
import type { QualityRowsPage, QualityRowsQuery, QualityIssueDetail } from "../types/quality";
import type { SelectionScope } from "../types/selection";

export interface NovelGuardBridge {
  getSnapshot(): Promise<AppSnapshot>;
  selectFolder(): Promise<void>;
  startScan(options?: Record<string, unknown>): Promise<void>;
  cancelRun(): Promise<void>;
  setWorkMode(mode: "scan" | "resolve" | "quality"): Promise<void>;
  queryReviewRows(query: ReviewRowsQuery): Promise<ReviewRowsPage>;
  queryQualityRows(query: QualityRowsQuery): Promise<QualityRowsPage>;
  getDuplicateGroupDetail(groupId: string): Promise<Record<string, unknown>>;
  getQualityIssueDetail(issueId: string): Promise<QualityIssueDetail>;
  getMovePreview(selection: SelectionScope): Promise<{ rows: unknown[] }>;
  applyResolvedActions(selection: SelectionScope): Promise<void>;
}
```

- [ ] **Step 3: Implement `mockBridge.ts`**

- Seed snapshot aligned with `Sample/MockUp/MockUp.jsx` `mockSnapshot` (folder path, counts).
- `queryReviewRows`: filter in-memory ~1284 generated rows (port `createReviewRows` logic from mockup); return `ReviewRowsPage` with `pageInfo.hasMore` when slicing.
- `queryQualityRows`: return issues where `integrity !== "OK"` or encoding not UTF-8.
- `getMovePreview` / `applyResolvedActions`: log `SelectionScope` to console; no file I/O.

- [ ] **Step 4: `SnapshotProvider`**

```tsx
// web/src/app/providers/SnapshotProvider.tsx
import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import type { AppSnapshot } from "../../types/snapshot";
import type { NovelGuardBridge } from "../../bridge/NovelGuardBridge";
import { mockBridge } from "../../bridge/mockBridge";

const BridgeContext = createContext<NovelGuardBridge>(mockBridge);
const SnapshotContext = createContext<AppSnapshot | null>(null);

export function SnapshotProvider({ children, bridge = mockBridge }: { children: ReactNode; bridge?: NovelGuardBridge }) {
  const [snapshot, setSnapshot] = useState<AppSnapshot | null>(null);
  useEffect(() => {
    let alive = true;
    const tick = async () => {
      const s = await bridge.getSnapshot();
      if (alive) setSnapshot(s);
    };
    tick();
    const id = setInterval(tick, 1000);
    return () => { alive = false; clearInterval(id); };
  }, [bridge]);
  if (!snapshot) return <div className="p-6 text-muted">Loading…</div>;
  return (
    <BridgeContext.Provider value={bridge}>
      <SnapshotContext.Provider value={snapshot}>{children}</SnapshotContext.Provider>
    </BridgeContext.Provider>
  );
}

export const useBridge = () => useContext(BridgeContext);
export const useSnapshot = () => {
  const s = useContext(SnapshotContext);
  if (!s) throw new Error("SnapshotProvider missing");
  return s;
};
```

- [ ] **Step 5: Verify** `cd web && npm run build`

- [ ] **Step 6: Commit** `[web] add DTO types and mock bridge`

---

## PR-2: AppShell + FileSummaryStrip + GlobalCommandBar

**Files:**
- Create: layout components under `web/src/components/layout/`
- Modify: `web/src/app/App.tsx`

- [ ] **Step 1: `AppShell.tsx`**

Grid per spec:

```tsx
// rows: header | sidebar+content | strip | command bar
<div className="grid min-h-screen grid-rows-[auto_1fr_auto_auto] bg-background text-on-surface">
```

- [ ] **Step 2: `AppSidebar.tsx`**

Routes: `work`, `settings`, `logs` — local state in `App.tsx` until router added (v1: `useState` route is OK).

- [ ] **Step 3: `FileSummaryStrip.tsx`**

Props: `library` from snapshot, `onOpenResolve`. CTA sets route `work` + calls `bridge.setWorkMode("resolve")` (v1: mode switch only per spec open item).

- [ ] **Step 4: `GlobalCommandBar.tsx`**

Props: `pipeline`, `hasPendingApply` from `snapshot.work.resolve`, handlers `onFullPipeline`, `onCancel`.

Implement preflight rule:

```typescript
function handleFullPipeline() {
  if (snapshot.work.resolve.hasPendingApply) {
    setPreflightOpen(true);
  } else {
    setSubflowOpen(true);
  }
}
```

- [ ] **Step 5: Wire `App.tsx` with placeholders for route content**

- [ ] **Step 6: Verify** dev smoke: `npm run dev` — shell visible, strip + bar at bottom

- [ ] **Step 7: Commit** `[web] AppShell strip and GlobalCommandBar`

---

## PR-3: WorkModeTabs + ScanWorkspace

**Files:**
- Create: `web/src/features/work/WorkRoute.tsx`, `WorkModeTabs.tsx`, `ScanWorkspace.tsx`

- [ ] **Step 1: `WorkModeTabs`**

Tabs: `scan` | `resolve` | `quality` — labels `스캔`, `검토 · 정리`, `품질`. Sync with `snapshot.work.activeMode` via `setWorkMode`.

- [ ] **Step 2: `ScanWorkspace`**

Sections: folder display, scan option chips, start/cancel buttons, result summary StatChips, CTA `검토 · 정리로 이동` → `setWorkMode("resolve")`.

**No file table** in this mode.

- [ ] **Step 3: `WorkRoute` shell** — render tabs + mode switch (resolve/quality placeholders).

- [ ] **Step 4: Compare visually to `Sample/MockUp/MockUp.jsx` `ScanWorkspace`**

- [ ] **Step 5: Commit** `[web] Scan workspace and mode tabs`

---

## PR-4: ResolveAndOrganizeWorkspace skeleton

**Files:**
- Create: `ResolveAndOrganizeWorkspace.tsx`, `FacetPanel.tsx`, `DetailPanel.tsx`, `BatchActionBar.tsx` (stubs)
- Create: `VirtualizedReviewGrid.tsx` (placeholder list)

- [ ] **Step 1: Layout `flex min-h-0 flex-1 flex-col`**

Header: title + StatChips (queue, groups, conflicts, approved) from `snapshot.work.resolve`.

- [ ] **Step 2: Three-column body**

`FacetPanel` (fixed width ~256px) | center placeholder | `DetailPanel` (360px).

- [ ] **Step 3: `BatchActionBar` stub** — disabled actions OK

- [ ] **Step 4: Commit** `[web] Resolve workspace layout skeleton`

---

## PR-5: queryReviewRows + TanStack Virtual grid

**Files:**
- Modify: `mockBridge.ts` (cursor pagination)
- Create: `web/src/features/work/resolve/VirtualizedReviewGrid.tsx`
- Modify: `ResolveAndOrganizeWorkspace.tsx`

- [ ] **Step 1: Cursor pagination in mock**

`queryReviewRows`: accept `cursor` as offset string; `limit` default 100; set `nextCursor` when more rows exist.

- [ ] **Step 2: `VirtualizedReviewGrid`**

Use `@tanstack/react-virtual`:

```typescript
import { useVirtualizer } from "@tanstack/react-virtual";

const rowVirtualizer = useVirtualizer({
  count: rows.length,
  getScrollElement: () => parentRef.current,
  estimateSize: () => 48,
  overscan: 8,
});
```

Columns (default visible): Status, Type, Name/Keeper, Action, Target, Confidence — map enums to Korean in cell renderers.

- [ ] **Step 3: Load rows in workspace**

On `viewMode` / filter / search change: call `bridge.queryReviewRows({ viewMode, filters: { search, status }, cursor: null, limit: 100 })`.

Append pages when user scrolls near end (`hasMore` → fetch `nextCursor`). **Do not** load all 1284 rows into React state at once in production path; mock may generate slice per request only.

- [ ] **Step 4: Performance check**

DevTools: scrolling 1000+ rows stays responsive; DOM node count stays ~visible window.

- [ ] **Step 5: Commit** `[web] virtualized review grid with queryReviewRows`

---

## PR-6: DetailPanel + SelectionScope + BatchActionBar

**Files:**
- Modify: `DetailPanel.tsx`, `BatchActionBar.tsx`, `ResolveAndOrganizeWorkspace.tsx`
- Modify: `web/src/types/selection.ts` usage

- [ ] **Step 1: Row selection state**

```typescript
const [explicitIds, setExplicitIds] = useState<string[]>([]);
const selection: SelectionScope =
  bulkQueryMode
    ? { type: "current_query", query: currentQuery, excludeRowIds: [] }
    : { type: "explicit_rows", rowIds: explicitIds };
```

- [ ] **Step 2: `DetailPanel`**

On row click: show keeper, move plan, encoding, integrity, collapsible JSON. Optional: `getDuplicateGroupDetail(groupId)` when `rowKind === "group"`.

- [ ] **Step 3: `BatchActionBar`**

Display: `3 selected` vs `412 in current filter (2 excluded)`.

Wire `이동 계획 미리보기` → `bridge.getMovePreview(selection)`.

- [ ] **Step 4: `FacetPanel`**

Wire view modes: `action`, `groups`, `move`, `all`, `conflicts` — updates `ReviewRowsQuery.viewMode`.

- [ ] **Step 5: Commit** `[web] selection scope detail and batch bar`

---

## PR-7: ApplySubflow + preflight pipeline dialogs

**Files:**
- Create: `ApplySubflowDialog.tsx`, `PreflightPipelineDialog.tsx`
- Modify: `GlobalCommandBar.tsx`, `App.tsx`

- [ ] **Step 1: `ApplySubflowDialog`**

Steps UI: Preview → Confirm → Apply. Apply button calls `applyResolvedActions` only on confirm. Progress UI **not** inside dialog — only `GlobalCommandBar` updates when `pipeline` running.

- [ ] **Step 2: `PreflightPipelineDialog`**

Lists blockers: `unreviewedCount`, `conflictCount`, `hasPendingApply`. Actions: `검토 · 정리로 이동` or `그래도 계속` (optional, spec-safe default: force resolve first).

- [ ] **Step 3: Wire GlobalCommandBar preflight** (PR-2 handler completes here)

- [ ] **Step 4: Commit** `[web] apply and preflight subflows`

---

## PR-8: QualityWorkspace read-heavy

**Files:**
- Create: `QualityWorkspace.tsx`, `quality/QualityIssueGrid.tsx`
- Modify: `mockBridge.ts` — `queryQualityRows`, `getQualityIssueDetail`

- [ ] **Step 1: `QualityWorkspace`**

Tabs or sections: Integrity | Encoding | Small file (stub list OK). Use `queryQualityRows({ issueType, cursor, limit })`.

- [ ] **Step 2: Grid**

Reuse virtualizer pattern from PR-5 (smaller row count OK in v1). Read-only actions; buttons show stub toast `v1: repair not available`.

- [ ] **Step 3: Detail** — `getQualityIssueDetail(issueId)` on row select

- [ ] **Step 4: Commit** `[web] Quality workspace read-only`

---

## PR-9: pywebview bridge integration smoke

**Files:**
- Create: `src/app/webview_main.py`, `src/app/bridge_api.py` (minimal stub implementing same method names)
- Create: `web/src/bridge/pywebviewBridge.ts`

- [ ] **Step 1: Python stub `BridgeApi` class**

Methods: `get_snapshot`, `query_review_rows` (json args) — return dicts matching DTO shape. No domain logic; static JSON OK for smoke.

Expose via:

```python
import webview

class BridgeApi:
    def get_snapshot(self):
        return {...}

if __name__ == "__main__":
    api = BridgeApi()
    webview.create_window("NovelGuard", "web/dist/index.html", js_api=api)
    webview.start()
```

- [ ] **Step 2: Build web assets**

```bash
cd web && npm run build
```

- [ ] **Step 3: `pywebviewBridge.ts`**

```typescript
export function createPywebviewBridge(): NovelGuardBridge {
  const api = (window as unknown as { pywebview: { api: Record<string, (...args: unknown[]) => Promise<unknown>> } }).pywebview.api;
  return {
    getSnapshot: () => api.get_snapshot() as Promise<AppSnapshot>,
    // map snake_case Python methods to camelCase TS interface
  };
}
```

- [ ] **Step 4: `SnapshotProvider` bridge selection**

```typescript
const bridge = typeof window !== "undefined" && "pywebview" in window
  ? createPywebviewBridge()
  : mockBridge;
```

- [ ] **Step 5: Smoke**

```bash
pip install pywebview  # if not in pyproject yet — add to pyproject optional [gui] with approval
python src/app/webview_main.py
```

Expected: window opens, strip + Resolve grid load from Python stub.

- [ ] **Step 6: Document run path in `docs/entry_points.md`** (create file if missing): `web` dev vs pywebview host.

- [ ] **Step 7: Commit** `[app] pywebview bridge smoke host`

---

## Verification (each PR)

| Check | Command |
|-------|---------|
| Web build | `cd web && npm run build` |
| Python gate (if `src/` touched) | `python scripts/verify_phase_completion.py` |
| Manual | Work → 3 modes; Resolve scroll; Apply dialog; Quality list; strip CTA → resolve mode |

---

## Spec coverage self-review

| Spec requirement | Plan task |
|------------------|-----------|
| Hybrid 3-mode Work | PR-3, PR-4..8 |
| Resolve = duplicate + move merged | PR-4..7 |
| Quality separate | PR-8 |
| No rows in AppSnapshot | PR-1 types; PR-1 mock |
| queryReviewRows + ReviewRowsPage | PR-1, PR-5 |
| queryQualityRows | PR-1, PR-8 |
| SelectionScope | PR-6 |
| GlobalCommandBar single progress | PR-2, PR-7 |
| Preflight full pipeline | PR-2, PR-7 |
| TanStack Virtual | PR-5 |
| TanStack Table (column tooling) | **PR-12** (deferred; Virtual-only grids in PR-5..11) |
| DESIGN.md tokens | PR-0 |
| pywebview js_api | PR-9 |
| FileSummaryStrip CTA | PR-2 |
| Destructive preview→confirm→apply | PR-7 |
| v1 out: Finalize apply, FileDock | Not in PR map |

**Open items from spec:** FileSummaryStrip CTA = mode switch only (PR-2). `hasPendingApply` wired in mock when preview open (PR-7).

---

## Plan changelog

| Date | Note |
|------|------|
| 2026-06-01 | Initial plan from approved spec; PR-0..PR-9 |
