# PR-12: Grid Perf Benchmark + TanStack Table Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Adopt `@tanstack/react-table` for Resolve and Quality grids (column defs, visibility, header sort) while keeping `@tanstack/react-virtual` for row windowing, and add automated perf guards that prove DOM row count stays bounded at 1k+ loaded rows.

**Architecture:** Extract a headless `VirtualizedDataGrid` that composes Table (columns, visibility, sort UI) + Virtual (row window). Review and Quality grids supply column definitions only. `mockBridge` gains server-side sort on filtered slices before pagination. Perf tests run in Vitest with `happy-dom` for DOM caps and `vitest bench` for data-path timing.

**Tech Stack:** React 19, TypeScript 6, `@tanstack/react-table` 8.21, `@tanstack/react-virtual` 3.13, Vitest 3, happy-dom, Playwright 1.49 (smoke extension only).

**Spec reference:** `docs/superpowers/specs/00-2026-06-01-novelguard-ui-overhaul-design.md` — Performance contract §, Default grid columns §, Grid stack decision §.

**Depends on:** PR-10 (`web/src/contracts/*`), PR-11 (E2E smoke, bridge errors) complete on `feat/web-ui-overhaul`.

## Implementation status

| Item | Status | Branch |
|------|--------|--------|
| PR-12 (Tasks 1–11) | **Done** | `feat/web-ui-overhaul` |

**Testing permission:**

```text
TEST_ALLOWED — Vitest perf/component tests under web/src/**/*.test.ts(x) and one Playwright spec extension for PR-12.

Rationale:
PR-12 acceptance requires measurable virtualization bounds and Table integration regressions; contract tests do not cover grid DOM or sort wiring.
Limit: no new Python test files; extend web/e2e/smoke.spec.ts by at most 2 tests.
```

**Non-goals (PR-12):** AG Grid, preview-token/stale-apply (PR-13), packaging/webview_main (PR-14), new Work screens, FileDock, repair/finalize, Python bridge sort (mock-only sort OK), column resize drag handles (defer), client-side full-library load, changing PR-10 contract validators.

---

## File map

| File | Responsibility |
|------|----------------|
| `web/package.json` | `happy-dom`, `@testing-library/react`, `test:perf`, `bench:grid` scripts |
| `web/vitest.config.ts` | `environmentMatchGlobs` for `*.test.tsx` |
| `web/src/components/grid/virtualWindow.ts` | Pure helpers: max visible rows, scroll near-end |
| `web/src/components/grid/virtualWindow.test.ts` | Unit thresholds (no DOM) |
| `web/src/components/grid/VirtualizedDataGrid.tsx` | Table + Virtual shell, header sort affordance |
| `web/src/components/grid/ColumnChooser.tsx` | Toggle optional columns; `localStorage` persistence |
| `web/src/components/grid/VirtualizedDataGrid.test.tsx` | DOM row cap @ 2000 logical rows |
| `web/src/features/work/resolve/reviewGridColumns.tsx` | `ColumnDef<ReviewRow>[]` + visibility groups |
| `web/src/features/work/resolve/VirtualizedReviewGrid.tsx` | Thin wrapper over `VirtualizedDataGrid` |
| `web/src/features/work/resolve/useReviewGridColumns.ts` | **Remove** after Table `columnVisibility` replaces responsive hide (or keep width-based hide merged into Table) |
| `web/src/features/work/quality/qualityGridColumns.tsx` | `ColumnDef<QualityRow>[]` |
| `web/src/features/work/quality/QualityIssueGrid.tsx` | Refactor to `VirtualizedDataGrid` |
| `web/src/features/work/QualityWorkspace.tsx` | Cursor pagination + `queryError` parity with Resolve |
| `web/src/bridge/mockData.ts` | `sortReviewRows`, optional `path` on `ReviewRow` mock |
| `web/src/bridge/mockBridge.ts` | Apply sort before `paginateRows` |
| `web/src/perf/gridDataPath.bench.ts` | Bench filter+paginate at 1284 rows |
| `web/e2e/smoke.spec.ts` | +2 tests: column chooser, header sort |
| `docs/entry_points.md` | `test:perf`, `bench:grid` commands |
| `docs/superpowers/specs/00-2026-06-01-novelguard-ui-overhaul-design.md` | Changelog line PR-12 |

---

## Acceptance criteria

```text
✓ npm run build pass
✓ npm run test:contracts pass (PR-10 regression)
✓ npm run test:perf pass (DOM cap + virtualWindow unit tests)
✓ npm run bench:grid completes with documented thresholds (no hard CI fail on bench noise — test:perf is gate)
✓ npm run test:e2e pass (9/9 after +2 tests)
✓ Resolve grid uses @tanstack/react-table column defs (grep flexRender or useReactTable in resolve feature)
✓ Optional columns toggled via ColumnChooser; persistence key novelguard.reviewGrid.columns.v1
✓ Header click sets ReviewRowsQuery.sort; mockBridge returns sorted page
✓ Quality grid uses same VirtualizedDataGrid; cursor pagination when >100 issues
✓ PR-13..14 scope not touched
```

### Performance thresholds (gate in `test:perf`)

| Metric | Threshold |
|--------|-----------|
| DOM row buttons in Resolve grid fixture | ≤ `2 * overscan + 3` (default overscan 8 → ≤ 19) at 2000 logical rows |
| `filterReviewRows` + `paginateRows` on 1284 rows | < 50 ms median over 20 iterations (unit test, not bench) |
| Loaded rows in workspace state after 3 pages | ≤ 300 (3 × limit 100) — existing behavior preserved |

---

### Task 1: Vitest component environment + scripts

**Files:**
- Modify: `web/package.json`
- Modify: `web/vitest.config.ts`
- Modify: `package.json` (repo root shortcuts)

- [ ] **Step 1: Add devDependencies**

In `web/package.json` `devDependencies`:

```json
"happy-dom": "^20.0.0",
"@testing-library/react": "^16.3.0",
"@testing-library/dom": "^10.4.0"
```

- [ ] **Step 2: Add scripts**

In `web/package.json` `scripts`:

```json
"test:perf": "vitest run src/components/grid src/perf",
"bench:grid": "vitest bench src/perf/gridDataPath.bench.ts"
```

Root `package.json` scripts:

```json
"test:perf": "npm run test:perf --prefix web",
"bench:grid": "npm run bench:grid --prefix web"
```

- [ ] **Step 3: Vitest environment match**

Replace `web/vitest.config.ts` with:

```typescript
import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    environment: "node",
    include: ["src/**/*.test.ts", "src/**/*.test.tsx"],
    environmentMatchGlobs: [
      ["src/**/*.test.tsx", "happy-dom"],
      ["src/components/**", "happy-dom"],
    ],
  },
});
```

- [ ] **Step 4: Install and smoke**

```bash
cd web
npm install
npm run test:contracts
```

Expected: PASS (existing).

- [ ] **Step 5: Commit**

```bash
git add web/package.json web/package-lock.json web/vitest.config.ts package.json
git commit -m "[web] PR-12 vitest happy-dom and perf scripts"
```

---

### Task 2: Virtual window helpers + unit tests

**Files:**
- Create: `web/src/components/grid/virtualWindow.ts`
- Create: `web/src/components/grid/virtualWindow.test.ts`

- [ ] **Step 1: Write failing unit tests**

Create `web/src/components/grid/virtualWindow.test.ts`:

```typescript
import { describe, expect, it } from "vitest";
import {
  maxRenderedRowSlots,
  isNearScrollEnd,
  filterPaginateLatencyBudgetMs,
} from "./virtualWindow";

describe("virtualWindow", () => {
  it("caps rendered slots to overscan window", () => {
    expect(maxRenderedRowSlots({ overscan: 8 })).toBe(19);
  });

  it("detects near-end scroll", () => {
    expect(
      isNearScrollEnd({ scrollTop: 880, clientHeight: 100, scrollHeight: 1000, threshold: 120 }),
    ).toBe(true);
    expect(
      isNearScrollEnd({ scrollTop: 100, clientHeight: 100, scrollHeight: 1000, threshold: 120 }),
    ).toBe(false);
  });

  it("documents filter+paginate budget", () => {
    expect(filterPaginateLatencyBudgetMs()).toBe(50);
  });
});
```

- [ ] **Step 2: Run — expect FAIL**

```bash
cd web
npx vitest run src/components/grid/virtualWindow.test.ts
```

Expected: FAIL — module not found.

- [ ] **Step 3: Implement helpers**

Create `web/src/components/grid/virtualWindow.ts`:

```typescript
export function maxRenderedRowSlots({ overscan }: { overscan: number }): number {
  // virtualizer renders ~viewport rows + 2*overscan; +1 header row slot in DOM tests
  return overscan * 2 + 3;
}

export function isNearScrollEnd({
  scrollTop,
  clientHeight,
  scrollHeight,
  threshold,
}: {
  scrollTop: number;
  clientHeight: number;
  scrollHeight: number;
  threshold: number;
}): boolean {
  return scrollTop + clientHeight >= scrollHeight - threshold;
}

/** Gate for mock filter+paginate unit timing (see gridDataPath test). */
export function filterPaginateLatencyBudgetMs(): number {
  return 50;
}
```

- [ ] **Step 4: Run — expect PASS**

```bash
cd web
npx vitest run src/components/grid/virtualWindow.test.ts
```

- [ ] **Step 5: Commit**

```bash
git add web/src/components/grid/virtualWindow.ts web/src/components/grid/virtualWindow.test.ts
git commit -m "[web] PR-12 virtual window helpers"
```

---

### Task 3: `VirtualizedDataGrid` core (Table + Virtual)

**Files:**
- Create: `web/src/components/grid/VirtualizedDataGrid.tsx`

- [ ] **Step 1: Create grid shell**

Create `web/src/components/grid/VirtualizedDataGrid.tsx`:

```tsx
import { useRef } from "react";
import {
  flexRender,
  getCoreRowModel,
  useReactTable,
  type ColumnDef,
  type OnChangeFn,
  type SortingState,
  type VisibilityState,
} from "@tanstack/react-table";
import { useVirtualizer } from "@tanstack/react-virtual";

export type VirtualizedDataGridProps<T> = {
  data: T[];
  columns: ColumnDef<T, unknown>[];
  getRowId: (row: T) => string;
  selectedRowId?: string | null;
  onSelectRow?: (row: T) => void;
  sorting?: SortingState;
  onSortingChange?: OnChangeFn<SortingState>;
  columnVisibility?: VisibilityState;
  onColumnVisibilityChange?: OnChangeFn<VisibilityState>;
  estimateRowHeight?: number;
  overscan?: number;
  onNearEnd?: () => void;
  loadingMore?: boolean;
  footer?: React.ReactNode;
  testId?: string;
  headerTestIdPrefix?: string;
};

export function VirtualizedDataGrid<T>({
  data,
  columns,
  getRowId,
  selectedRowId,
  onSelectRow,
  sorting = [],
  onSortingChange,
  columnVisibility,
  onColumnVisibilityChange,
  estimateRowHeight = 48,
  overscan = 8,
  onNearEnd,
  loadingMore,
  footer,
  testId,
  headerTestIdPrefix = "grid-header",
}: VirtualizedDataGridProps<T>) {
  const parentRef = useRef<HTMLDivElement>(null);

  const table = useReactTable({
    data,
    columns,
    state: { sorting, columnVisibility },
    onSortingChange,
    onColumnVisibilityChange,
    getCoreRowModel: getCoreRowModel(),
    getRowId: (row) => getRowId(row),
  });

  const { rows } = table.getRowModel();

  const rowVirtualizer = useVirtualizer({
    count: rows.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => estimateRowHeight,
    overscan,
  });

  const handleScroll = () => {
    const el = parentRef.current;
    if (!el || !onNearEnd) return;
    if (el.scrollTop + el.clientHeight >= el.scrollHeight - 120) {
      onNearEnd();
    }
  };

  const gridTemplate = table
    .getVisibleLeafColumns()
    .map((col) => col.columnDef.meta?.gridWidth ?? "minmax(0,1fr)")
    .join(" ");

  return (
    <section
      data-testid={testId}
      className="flex min-h-0 min-w-0 flex-1 flex-col overflow-x-hidden border-r border-outline bg-background"
    >
      <div
        className="grid border-b border-outline bg-surface px-3 py-2 text-xs font-semibold uppercase tracking-wide text-muted"
        style={{ gridTemplateColumns: gridTemplate }}
      >
        {table.getHeaderGroups().map((hg) =>
          hg.headers.map((header) => {
            const canSort = header.column.getCanSort();
            const sorted = header.column.getIsSorted();
            return (
              <button
                key={header.id}
                type="button"
                data-testid={`${headerTestIdPrefix}-${header.id}`}
                disabled={!canSort}
                onClick={canSort ? header.column.getToggleSortingHandler() : undefined}
                className={`truncate text-left ${canSort ? "cursor-pointer hover:text-on-surface" : "cursor-default"}`}
              >
                {flexRender(header.column.columnDef.header, header.getContext())}
                {sorted === "asc" ? " ▲" : sorted === "desc" ? " ▼" : null}
              </button>
            );
          }),
        )}
      </div>
      <div ref={parentRef} className="min-h-0 flex-1 overflow-auto" onScroll={handleScroll}>
        <div className="relative w-full" style={{ height: `${rowVirtualizer.getTotalSize()}px` }}>
          {rowVirtualizer.getVirtualItems().map((virtualRow) => {
            const row = rows[virtualRow.index];
            const original = row.original;
            const selected = selectedRowId === row.id;
            return (
              <div
                key={row.id}
                role="button"
                tabIndex={0}
                data-testid="grid-row"
                onClick={() => onSelectRow?.(original)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") onSelectRow?.(original);
                }}
                className={`absolute left-0 grid w-full items-center border-b border-outline px-3 text-left text-sm transition ${
                  selected
                    ? "bg-primary/15 outline outline-1 outline-primary/40"
                    : "bg-background hover:bg-hover"
                }`}
                style={{
                  gridTemplateColumns: gridTemplate,
                  height: `${virtualRow.size}px`,
                  transform: `translateY(${virtualRow.start}px)`,
                }}
              >
                {row.getVisibleCells().map((cell) => (
                  <div key={cell.id} className="min-w-0 truncate">
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </div>
                ))}
              </div>
            );
          })}
        </div>
      </div>
      {footer}
    </section>
  );
}
```

Add to a shared `web/src/components/grid/gridColumnMeta.ts` (create in Step 2 of Task 4) — `meta.gridWidth` typing:

```typescript
import "@tanstack/react-table";

declare module "@tanstack/react-table" {
  interface ColumnMeta<TData, TValue> {
    gridWidth?: string;
  }
}
```

- [ ] **Step 2: Verify compile**

```bash
cd web
npm run build
```

Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add web/src/components/grid
git commit -m "[web] PR-12 VirtualizedDataGrid Table+Virtual shell"
```

---

### Task 4: Review column definitions + refactor grid

**Files:**
- Create: `web/src/components/grid/gridColumnMeta.ts`
- Create: `web/src/features/work/resolve/reviewGridColumns.tsx`
- Modify: `web/src/features/work/resolve/VirtualizedReviewGrid.tsx`
- Delete or narrow: `web/src/features/work/resolve/useReviewGridColumns.ts`

- [ ] **Step 1: Column meta module**

Create `web/src/components/grid/gridColumnMeta.ts` (declare module block above).

- [ ] **Step 2: Review columns**

Create `web/src/features/work/resolve/reviewGridColumns.tsx`:

```tsx
import { createColumnHelper } from "@tanstack/react-table";
import type { ReviewRow } from "../../../types/review";
import { proposedActionLabel, reviewStatusLabel, reviewTypeLabel } from "../../../lib/labels";

const helper = createColumnHelper<ReviewRow>();

export const REVIEW_GRID_STORAGE_KEY = "novelguard.reviewGrid.columns.v1";

export const defaultReviewColumnVisibility = {
  status: true,
  type: true,
  name: true,
  proposedAction: true,
  targetFolder: true,
  confidence: true,
  encoding: false,
  integrity: false,
  path: false,
  sizeBytes: false,
};

export function buildReviewGridColumns() {
  return [
    helper.accessor("status", {
      header: "Status",
      enableSorting: true,
      meta: { gridWidth: "5rem" },
      cell: (ctx) => (
        <span className={ctx.getValue() === "conflict" ? "font-semibold text-error" : ""}>
          {reviewStatusLabel[ctx.getValue()]}
        </span>
      ),
    }),
    helper.accessor("type", {
      header: "Type",
      enableSorting: true,
      meta: { gridWidth: "5rem" },
      cell: (ctx) => <span className="text-muted">{reviewTypeLabel[ctx.getValue()]}</span>,
    }),
    helper.accessor("name", {
      id: "name",
      header: "Name / Keeper",
      enableSorting: true,
      meta: { gridWidth: "minmax(0,1fr)" },
      cell: (ctx) => {
        const row = ctx.row.original;
        return (
          <>
            <span className="block truncate font-medium text-on-surface">{row.name}</span>
            <span className="block truncate text-xs text-muted">keeper: {row.keeperLabel}</span>
          </>
        );
      },
    }),
    helper.accessor("proposedAction", {
      header: "Action",
      enableSorting: true,
      meta: { gridWidth: "7rem" },
      cell: (ctx) => (
        <span className="text-on-surface-variant">{proposedActionLabel[ctx.getValue()]}</span>
      ),
    }),
    helper.accessor("targetFolder", {
      header: "Target",
      enableSorting: true,
      meta: { gridWidth: "7rem" },
      cell: (ctx) => <span className="text-muted">{ctx.getValue() ?? "—"}</span>,
    }),
    helper.accessor("confidence", {
      header: "Conf.",
      enableSorting: true,
      meta: { gridWidth: "4.5rem" },
      cell: (ctx) => (
        <span className="tabular-nums text-on-surface-variant">{ctx.getValue() ?? "—"}</span>
      ),
    }),
    helper.accessor("encoding", {
      header: "Encoding",
      enableSorting: true,
      meta: { gridWidth: "6rem" },
    }),
    helper.accessor("integrity", {
      header: "Integrity",
      enableSorting: true,
      meta: { gridWidth: "8rem" },
    }),
    helper.accessor((row) => row.path ?? "—", {
      id: "path",
      header: "Path",
      enableSorting: false,
      meta: { gridWidth: "minmax(0,1.2fr)" },
    }),
    helper.accessor("sizeBytes", {
      header: "Size",
      enableSorting: true,
      meta: { gridWidth: "5rem" },
      cell: (ctx) => {
        const v = ctx.getValue();
        return v ? `${(v / (1024 * 1024)).toFixed(1)} MB` : "—";
      },
    }),
  ];
}
```

- [ ] **Step 3: Refactor `VirtualizedReviewGrid.tsx`**

Replace body with Table-powered grid:

```tsx
import { useMemo, useState } from "react";
import type { SortingState, VisibilityState } from "@tanstack/react-table";
import { VirtualizedDataGrid } from "../../../components/grid/VirtualizedDataGrid";
import type { ReviewRow } from "../../../types/review";
import {
  REVIEW_GRID_STORAGE_KEY,
  buildReviewGridColumns,
  defaultReviewColumnVisibility,
} from "./reviewGridColumns";

function loadVisibility(): VisibilityState {
  try {
    const raw = localStorage.getItem(REVIEW_GRID_STORAGE_KEY);
    return raw ? { ...defaultReviewColumnVisibility, ...JSON.parse(raw) } : defaultReviewColumnVisibility;
  } catch {
    return defaultReviewColumnVisibility;
  }
}

export function VirtualizedReviewGrid({
  rows,
  selectedRowId,
  onSelectRow,
  onNearEnd,
  loadingMore,
  sorting,
  onSortingChange,
}: {
  rows: ReviewRow[];
  selectedRowId: string | null;
  onSelectRow: (row: ReviewRow) => void;
  onNearEnd?: () => void;
  loadingMore?: boolean;
  sorting: SortingState;
  onSortingChange: (updater: SortingState) => void;
}) {
  const columns = useMemo(() => buildReviewGridColumns(), []);
  const [columnVisibility, setColumnVisibility] = useState<VisibilityState>(loadVisibility);

  const persistVisibility = (next: VisibilityState) => {
    setColumnVisibility(next);
    localStorage.setItem(REVIEW_GRID_STORAGE_KEY, JSON.stringify(next));
  };

  return (
    <VirtualizedDataGrid
      testId="resolve-review-grid"
      headerTestIdPrefix="resolve-grid-header"
      data={rows}
      columns={columns}
      getRowId={(row) => row.id}
      selectedRowId={selectedRowId}
      onSelectRow={onSelectRow}
      sorting={sorting}
      onSortingChange={(updater) => {
        const next = typeof updater === "function" ? updater(sorting) : updater;
        onSortingChange(next);
      }}
      columnVisibility={columnVisibility}
      onColumnVisibilityChange={(updater) => {
        const next = typeof updater === "function" ? updater(columnVisibility) : updater;
        persistVisibility(next);
      }}
      onNearEnd={onNearEnd}
      loadingMore={loadingMore}
      footer={
        <div className="flex items-center justify-between border-t border-outline bg-surface px-4 py-2 text-xs text-muted">
          <span>
            {rows.length.toLocaleString()} loaded rows
            {loadingMore ? " · loading…" : ""}
          </span>
        </div>
      }
    />
  );
}
```

Remove `useReviewGridColumns.ts` imports from this file; delete file if unused.

- [ ] **Step 4: Build**

```bash
cd web
npm run build
```

- [ ] **Step 5: Commit**

```bash
git add web/src/features/work/resolve web/src/components/grid/gridColumnMeta.ts
git commit -m "[web] PR-12 review grid TanStack Table columns"
```

---

### Task 5: Column chooser UI

**Files:**
- Create: `web/src/components/grid/ColumnChooser.tsx`
- Modify: `web/src/features/work/ResolveAndOrganizeWorkspace.tsx`

- [ ] **Step 1: ColumnChooser component**

Create `web/src/components/grid/ColumnChooser.tsx`:

```tsx
import type { VisibilityState } from "@tanstack/react-table";

const LABELS: Record<string, string> = {
  encoding: "Encoding",
  integrity: "Integrity",
  path: "Path",
  sizeBytes: "Size",
};

export function ColumnChooser({
  visibility,
  optionalKeys,
  onChange,
}: {
  visibility: VisibilityState;
  optionalKeys: string[];
  onChange: (key: string, visible: boolean) => void;
}) {
  return (
    <details className="relative text-sm" data-testid="grid-column-chooser">
      <summary className="cursor-pointer list-none rounded-md border border-outline px-3 py-1.5 text-on-surface-variant hover:bg-hover">
        열 선택
      </summary>
      <div className="absolute right-0 z-20 mt-1 min-w-[12rem] rounded-md border border-outline bg-surface-elevated p-2 shadow-lg">
        {optionalKeys.map((key) => (
          <label key={key} className="flex items-center gap-2 py-1">
            <input
              type="checkbox"
              data-testid={`column-toggle-${key}`}
              checked={Boolean(visibility[key])}
              onChange={(e) => onChange(key, e.target.checked)}
            />
            <span>{LABELS[key] ?? key}</span>
          </label>
        ))}
      </div>
    </details>
  );
}
```

- [ ] **Step 2: Wire in Resolve header**

In `ResolveAndOrganizeWorkspace.tsx`, lift `columnVisibility` state from grid or pass chooser callbacks into `VirtualizedReviewGrid` via props `columnChooserSlot`. Minimal pattern: export `optionalReviewColumnKeys = ["encoding","integrity","path","sizeBytes"]` from `reviewGridColumns.tsx` and render `<ColumnChooser />` beside StatChips; share visibility state via React state in workspace passed to grid.

Add props to `VirtualizedReviewGrid`:

```typescript
columnVisibility: VisibilityState;
onColumnVisibilityChange: (next: VisibilityState) => void;
columnChooser?: React.ReactNode;
```

Render chooser in workspace:

```tsx
<ColumnChooser
  visibility={columnVisibility}
  optionalKeys={["encoding", "integrity", "path", "sizeBytes"]}
  onChange={(key, visible) =>
    setColumnVisibility((prev) => ({ ...prev, [key]: visible }))
  }
/>
```

- [ ] **Step 3: Commit**

```bash
git add web/src/components/grid/ColumnChooser.tsx web/src/features/work
git commit -m "[web] PR-12 column chooser for review grid"
```

---

### Task 6: Sort state + mockBridge server-side sort

**Files:**
- Modify: `web/src/bridge/mockData.ts`
- Modify: `web/src/bridge/mockBridge.ts`
- Modify: `web/src/features/work/ResolveAndOrganizeWorkspace.tsx`

- [ ] **Step 1: Add path + sort helper**

In `mockData.ts`, extend row factory:

```typescript
path: `/library/raw/${index + 1}/${FILE_NAMES[index % FILE_NAMES.length]}`,
```

Add:

```typescript
import type { ReviewRowsQuery } from "../types/review";

export function sortReviewRows(rows: ReviewRow[], sort?: ReviewRowsQuery["sort"]): ReviewRow[] {
  if (!sort?.field) return rows;
  const dir = sort.direction === "desc" ? -1 : 1;
  const field = sort.field as keyof ReviewRow;
  return [...rows].sort((a, b) => {
    const av = a[field];
    const bv = b[field];
    if (av == null && bv == null) return 0;
    if (av == null) return 1;
    if (bv == null) return -1;
    if (typeof av === "number" && typeof bv === "number") return (av - bv) * dir;
    return String(av).localeCompare(String(bv), "ko") * dir;
  });
}
```

- [ ] **Step 2: mockBridge apply sort**

In `queryReviewRows` handler after `filterReviewRows`:

```typescript
const filtered = filterReviewRows(getAllReviewRows(), query);
const sorted = sortReviewRows(filtered, query.sort);
const { slice, nextCursor, hasMore } = paginateRows(sorted, query.cursor, clampQueryLimit(query.limit));
```

- [ ] **Step 3: Wire sorting state in workspace**

In `ResolveAndOrganizeWorkspace.tsx`:

```typescript
import type { SortingState } from "@tanstack/react-table";

const [sorting, setSorting] = useState<SortingState>([]);

const currentQuery = useMemo<ReviewRowsQuery>(() => {
  const primary = sorting[0];
  return {
    viewMode,
    filters: { search: search || undefined },
    cursor: null,
    limit: 100,
    sort: primary
      ? { field: primary.id, direction: primary.desc ? "desc" : "asc" }
      : undefined,
  };
}, [viewMode, search, sorting]);
```

Pass `sorting` / `setSorting` to `VirtualizedReviewGrid`.

- [ ] **Step 4: Unit test sort**

Create `web/src/bridge/mockData.sort.test.ts`:

```typescript
import { describe, expect, it } from "vitest";
import { getAllReviewRows, sortReviewRows } from "./mockData";

describe("sortReviewRows", () => {
  it("orders by name ascending", () => {
    const rows = getAllReviewRows(20);
    const sorted = sortReviewRows(rows, { field: "name", direction: "asc" });
    expect(sorted[0].name <= sorted[1].name).toBe(true);
  });
});
```

Run:

```bash
cd web
npx vitest run src/bridge/mockData.sort.test.ts
```

- [ ] **Step 5: Commit**

```bash
git add web/src/bridge web/src/features/work/ResolveAndOrganizeWorkspace.tsx
git commit -m "[web] PR-12 server-side sort via mockBridge"
```

---

### Task 7: Quality grid Table + pagination parity

**Files:**
- Create: `web/src/features/work/quality/qualityGridColumns.tsx`
- Modify: `web/src/features/work/quality/QualityIssueGrid.tsx`
- Modify: `web/src/features/work/QualityWorkspace.tsx`

- [ ] **Step 1: Quality columns**

Create `web/src/features/work/quality/qualityGridColumns.tsx` with `createColumnHelper<QualityRow>()` — columns: name (`minmax(0,1fr)`), encoding (`6rem`), integrity (`8rem`), severity (optional hidden by default).

- [ ] **Step 2: Refactor `QualityIssueGrid`**

Use `VirtualizedDataGrid` with `testId="quality-issue-grid"`, `estimateRowHeight={44}`, `overscan={6}`.

- [ ] **Step 3: Pagination in `QualityWorkspace`**

Mirror Resolve pattern:

```typescript
const [rows, setRows] = useState<QualityRow[]>([]);
const [nextCursor, setNextCursor] = useState<string | null>(null);
const [loadingMore, setLoadingMore] = useState(false);

const loadPage = useCallback(async (cursor: string | null, append: boolean) => {
  const page = await bridge.queryQualityRows({ issueType, cursor, limit: 100 });
  setNextCursor(page.pageInfo.nextCursor);
  setRows((prev) => (append ? [...prev, ...page.rows] : page.rows));
}, [bridge, issueType]);
```

Wire `onNearEnd` when `nextCursor` set.

- [ ] **Step 4: Build + contracts**

```bash
cd web
npm run build
npm run test:contracts
```

- [ ] **Step 5: Commit**

```bash
git add web/src/features/work/quality web/src/features/work/QualityWorkspace.tsx
git commit -m "[web] PR-12 quality grid Table+Virtual pagination"
```

---

### Task 8: DOM perf test + data-path timing

**Files:**
- Create: `web/src/components/grid/VirtualizedDataGrid.test.tsx`
- Create: `web/src/perf/gridDataPath.test.ts`
- Create: `web/src/perf/gridDataPath.bench.ts`

- [ ] **Step 1: DOM cap test**

Create `web/src/components/grid/VirtualizedDataGrid.test.tsx`:

```tsx
import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { createColumnHelper } from "@tanstack/react-table";
import { VirtualizedDataGrid } from "./VirtualizedDataGrid";
import { maxRenderedRowSlots } from "./virtualWindow";

type Row = { id: string; name: string };

const helper = createColumnHelper<Row>();
const columns = [
  helper.accessor("name", { header: "Name", meta: { gridWidth: "1fr" } }),
];

describe("VirtualizedDataGrid perf", () => {
  it("renders bounded DOM rows for 2000 logical rows", () => {
    const data = Array.from({ length: 2000 }, (_, i) => ({ id: `r-${i}`, name: `Row ${i}` }));
    const { container } = render(
      <div style={{ height: 400, width: 800, display: "flex" }}>
        <VirtualizedDataGrid
          testId="perf-grid"
          data={data}
          columns={columns}
          getRowId={(r) => r.id}
          overscan={8}
        />
      </div>,
    );
    const domRows = container.querySelectorAll('[data-testid="grid-row"]');
    expect(domRows.length).toBeLessThanOrEqual(maxRenderedRowSlots({ overscan: 8 }));
  });
});
```

- [ ] **Step 2: Data-path timing test**

Create `web/src/perf/gridDataPath.test.ts`:

```typescript
import { describe, expect, it } from "vitest";
import { filterReviewRows, getAllReviewRows, paginateRows } from "../bridge/mockData";
import { filterPaginateLatencyBudgetMs } from "../components/grid/virtualWindow";

describe("grid data path", () => {
  it("filter+paginate 1284 rows under budget", () => {
    const all = getAllReviewRows(1284);
    const query = { viewMode: "all" as const, cursor: null, limit: 100 };
    const times: number[] = [];
    for (let i = 0; i < 20; i++) {
      const t0 = performance.now();
      const filtered = filterReviewRows(all, query);
      paginateRows(filtered, null, 100);
      times.push(performance.now() - t0);
    }
    times.sort((a, b) => a - b);
    const median = times[Math.floor(times.length / 2)];
    expect(median).toBeLessThan(filterPaginateLatencyBudgetMs());
  });
});
```

- [ ] **Step 3: Vitest bench (informational)**

Create `web/src/perf/gridDataPath.bench.ts`:

```typescript
import { bench, describe } from "vitest";
import { filterReviewRows, getAllReviewRows, paginateRows } from "../bridge/mockData";

const all = getAllReviewRows(1284);
const query = { viewMode: "all" as const, cursor: null, limit: 100 };

describe("grid data path bench", () => {
  bench("filter+paginate page", () => {
    const filtered = filterReviewRows(all, query);
    paginateRows(filtered, null, 100);
  });
});
```

- [ ] **Step 4: Run perf gate**

```bash
cd web
npm run test:perf
```

Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add web/src/components/grid/VirtualizedDataGrid.test.tsx web/src/perf
git commit -m "[web] PR-12 grid perf tests and bench"
```

---

### Task 9: E2E — column chooser + sort

**Files:**
- Modify: `web/e2e/smoke.spec.ts`

- [ ] **Step 1: Add tests**

Append to `web/e2e/smoke.spec.ts`:

```typescript
test("review column chooser toggles encoding column", async ({ page }) => {
  await page.goto("/");
  await page.getByTestId("work-mode-tab-resolve").click();
  await expect(page.getByTestId("resolve-review-grid")).toBeVisible();
  await page.getByTestId("grid-column-chooser").click();
  await page.getByTestId("column-toggle-encoding").check();
  await expect(page.getByTestId("resolve-grid-header-encoding")).toBeVisible();
});

test("review grid header sort triggers sorted fetch", async ({ page }) => {
  await page.goto("/");
  await page.getByTestId("work-mode-tab-resolve").click();
  await page.getByTestId("resolve-grid-header-name").click();
  await expect(page.getByTestId("resolve-grid-header-name")).toContainText("▼");
});
```

- [ ] **Step 2: Run E2E**

```bash
cd web
npm run test:e2e
```

Expected: 9/9 pass.

- [ ] **Step 3: Commit**

```bash
git add web/e2e/smoke.spec.ts
git commit -m "[web] PR-12 E2E column chooser and sort smoke"
```

---

### Task 10: Spec changelog + entry_points

**Files:**
- Modify: `docs/superpowers/specs/00-2026-06-01-novelguard-ui-overhaul-design.md`
- Modify: `docs/entry_points.md`
- Modify: `docs/superpowers/plans/000-2026-06-01-novelguard-ui-overhaul.md` (PR-12 row in status table)

- [ ] **Step 1: Spec changelog**

Append to changelog table in spec:

```markdown
| 2026-06-01 | PR-12: TanStack Table column defs + chooser; VirtualizedDataGrid; Vitest perf gates |
```

- [ ] **Step 2: entry_points.md**

Append:

```markdown
## Grid perf (PR-12)

```bash
cd web
npm run test:perf
npm run bench:grid
```
```

- [ ] **Step 3: Overhaul plan status row**

In `000-2026-06-01-novelguard-ui-overhaul.md` implementation status table add:

```markdown
| PR-12 | **Planned** | `003-2026-06-01-novelguard-ui-grid-perf.md` |
```

(Change to **Done** when implementation completes.)

- [ ] **Step 4: Commit**

```bash
git add docs/superpowers/specs docs/entry_points.md docs/superpowers/plans/000-2026-06-01-novelguard-ui-overhaul.md
git commit -m "[docs] PR-12 grid perf run path and spec changelog"
```

---

### Task 11: Full verification

- [ ] **Step 1: Web**

```bash
cd web
npm run build
npm run test:contracts
npm run test:perf
npm run test:e2e
```

Expected: all PASS.

- [ ] **Step 2: Python gate**

```bash
python scripts/verify_phase_completion.py
```

Expected: PASS (no Python changes expected).

- [ ] **Step 3: Optional bench (informational)**

```bash
cd web
npm run bench:grid
```

Record median in PR description; not a merge blocker if bench noisy on CI.

---

## Spec coverage self-review

| Spec requirement | Plan task |
|------------------|-----------|
| Performance contract: DOM window only | Task 2, 8 |
| Performance contract: server-side page, no full library in state | Task 6, 7 (preserve 100/page) |
| Grid stack: TanStack Virtual + Table | Task 3, 4, 7 |
| Default + hidden columns (chooser) | Task 4, 5 |
| NN/g find/compare via sort + column toggle | Task 6, 5 |
| Quality virtualized when large | Task 7 |
| DESIGN.md tokens only | Task 3–7 (no new hex) |
| queryReviewRows sort field | Task 6 |
| v2 FileDock / push snapshot | Non-goals |

**Gaps intentionally deferred:** column resize drag (v2), Python `BridgeApi` sort, PR-13 apply tokens, PR-14 packaging, AG Grid.

---

## Plan changelog

| Date | Note |
|------|------|
| 2026-06-01 | Initial PR-12 plan; TEST_ALLOWED Vitest perf + 2 E2E tests |

---

## Execution handoff

Plan complete and saved to `docs/superpowers/plans/003-2026-06-01-novelguard-ui-grid-perf.md`.

**Two execution options:**

1. **Subagent-Driven (recommended)** — fresh subagent per task, spec compliance review then code quality review between tasks (`subagent-driven-development`).

2. **Inline Execution** — run tasks in this session with checkpoints (`executing-plans`).

Which approach?
