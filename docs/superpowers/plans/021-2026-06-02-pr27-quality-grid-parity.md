# PR-27: Quality Grid Parity with Resolve — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire Quality workspace grid to `queryQualityRows` sort contract (Python + mock parity), expand to six columns with chooser/resize/responsive hide/footer, and add perf/DOM cap tests — read-only; no Resolve chooser backfill.

**Architecture:** Sort + whitelist live in `quality_query.py` and shared `sortQualityRows` in TS; `BridgeApi` maps `QualityQueryError` to JSON rejection for `BridgeCallError`. UI mirrors Resolve: state in `QualityWorkspace`, thin `VirtualizedQualityGrid`, user visibility ∩ responsive width inside `mergeColumnVisibility`. No new bridge RPCs.

**Tech Stack:** Python 3.12 (`src/application/quality_query.py`, `src/app/bridge_contract.py`); React 19 + TanStack Table/Virtual (`web/`); Vitest + existing pytest contract module.

**Spec:** [015-2026-06-02-quality-grid-parity-design.md](../specs/015-2026-06-02-quality-grid-parity-design.md) (**approved** 2026-06-02 — LOCK-27, D1–D7)

**Plan status:** **Proposed** — awaiting human approval before Task 1+

**Prerequisite:** Spec 015 approved; PR-26 on branch/main recommended; PR-21 detail drawer intact

**Parent:** [002 PR-26..30 roadmap](../roadmap/002-2026-06-02-pr26-pr30-platform-polish-roadmap.md)

**Test policy:** Extend **`tests/test_bridge_contract.py`**, **`web/src/bridge/bridgeParity.test.ts`**, **`web/src/components/grid/VirtualizedDataGrid.test.tsx`**, optionally **`web/e2e/smoke.spec.ts`** — **no new test files** without `TEST_ALLOWED`.

**Scope freeze (LOCK-27):** No Resolve ColumnChooser backfill; no repair/apply/FileDock/AG Grid; no `suggestedAction` column; no new bridge methods; no second `getSnapshot()` poll loop in Quality workspace.

---

## Plan-locked constants

| Constant | Value |
|----------|--------|
| Sort whitelist | `name`, `path`, `issueType`, `severity`, `encoding`, `integrity` |
| Reject reason | `INVALID_SORT_FIELD` |
| Columns storage | `novelguard.qualityGrid.columns.v1` |
| Sizing storage | `novelguard.qualityGrid.sizing.v1` |
| Default visible | `name`, `severity`, `encoding`, `integrity` |
| Default hidden (chooser) | `path`, `issueType` |
| Perf logical rows | `2000` |
| Query limit | `100` default (unchanged) |
| Revision reload source | `snapshot.work.resolve.libraryRevision` |

### Severity ordinal

```text
error = 0, warning = 1   # lower sorts first in asc
```

---

## File map

| File | Action |
|------|--------|
| `src/app/bridge_contract.py` | **Modify** — `QualityQueryError`, `QUALITY_SORT_FIELDS` |
| `src/application/quality_query.py` | **Modify** — whitelist, deterministic sort, tie-break |
| `src/app/bridge_api.py` | **Modify** — catch `QualityQueryError` on `query_quality_rows` |
| `tests/test_bridge_contract.py` | **Extend** — sort, reject, stable order, Korean fixture |
| `web/src/bridge/mockData.ts` | **Modify** — `sortQualityRows`, `textSortKey` |
| `web/src/bridge/mockBridge.ts` | **Modify** — sort before paginate in `queryQualityRows` |
| `web/src/bridge/parseBridgeRejection.ts` | **Modify** — recognize `INVALID_SORT_FIELD` |
| `web/src/bridge/bridgeParity.test.ts` | **Extend** — mock sort parity + reject |
| `web/src/features/work/quality/qualityGridColumns.tsx` | **Modify** — six columns, storage keys, defaults |
| `web/src/features/work/quality/qualityGridLayout.ts` | **Create** — `mergeQualityColumnVisibility` |
| `web/src/features/work/quality/qualityGridPersistence.ts` | **Create** — load/save columns + sizing (optional split) |
| `web/src/components/grid/ColumnChooser.tsx` | **Create** — shared UI, Quality-only wire |
| `web/src/features/work/quality/VirtualizedQualityGrid.tsx` | **Create** — wrapper + footer |
| `web/src/features/work/quality/QualityIssueGrid.tsx` | **Modify** — re-export or thin delegate to wrapper |
| `web/src/features/work/QualityWorkspace.tsx` | **Modify** — sort, visibility, sizing, loading, revision reload, chooser |
| `web/src/components/grid/VirtualizedDataGrid.test.tsx` | **Extend** — Quality perf fixture |
| `web/e2e/smoke.spec.ts` | **Extend** (optional) — sort + chooser smokes |
| `docs/superpowers/specs/015-2026-06-02-quality-grid-parity-design.md` | **Modify** — link plan status when done |
| `docs/superpowers/roadmap/002-2026-06-02-pr26-pr30-platform-polish-roadmap.md` | **Modify** — PR-27 plan approved / done rows |

**Path note:** Spec related path `specs/compelete/009-...` matches repo folder spelling (`compelete/`) — do not rename.

---

## LOCK-P27-1 — Green commits

Every task commit must leave touched tests green:

- Python: `pytest tests/test_bridge_contract.py -k quality -q` (or full contract file)
- Web: `cd web && npm run test -- src/bridge/bridgeParity.test.ts src/components/grid/VirtualizedDataGrid.test.tsx`

**Forbidden:** commit with failing contract/parity tests on touched surfaces.

---

### Task 0: Plan approval gate

**Human gate — do not implement Tasks 1–10 until approved.**

- [ ] Reviewer confirms plan matches spec 015 LOCK-27 and scope freeze
- [ ] Update this file: `Plan status: **Approved** (YYYY-MM-DD)`
- [ ] Optional: roadmap PR-27 row → plan approved

---

### Task 1: Backend quality sort contract + `INVALID_SORT_FIELD`

**Files:**
- Modify: `src/app/bridge_contract.py`
- Modify: `src/application/quality_query.py`
- Modify: `src/app/bridge_api.py`
- Test: `tests/test_bridge_contract.py`

- [ ] **Step 1: Add `QualityQueryError` and whitelist in `bridge_contract.py`**

```python
QUALITY_SORT_FIELDS = frozenset(
    {"name", "path", "issueType", "severity", "encoding", "integrity"}
)


class QualityQueryError(ValueError):
    def __init__(self, reason: str, message: str | None = None) -> None:
        self.reason = reason
        super().__init__(message or reason)

    def __str__(self) -> str:
        return json.dumps({"reason": self.reason}, ensure_ascii=False)
```

- [ ] **Step 2: Replace `_sort_rows` in `quality_query.py`**

Add module helpers:

```python
import unicodedata

_SEVERITY_ORDINAL = {"error": 0, "warning": 1}


def _text_sort_key(value: Any) -> str:
    if not isinstance(value, str):
        value = "" if value is None else str(value)
    return unicodedata.normalize("NFC", value).casefold()


def _validate_sort_field(query: dict[str, Any]) -> None:
    sort = query.get("sort")
    if not isinstance(sort, dict):
        return
    field = sort.get("field")
    if not field:
        return
    if field not in QUALITY_SORT_FIELDS:
        raise QualityQueryError("INVALID_SORT_FIELD")
```

Stable sort with tie-break:

```python
def _sort_rows(rows: list[dict[str, Any]], query: dict[str, Any]) -> list[dict[str, Any]]:
    _validate_sort_field(query)
    sort = query.get("sort")
    if not isinstance(sort, dict) or not sort.get("field"):
        return list(rows)

    field = str(sort["field"])
    reverse = sort.get("direction", "asc") == "desc"

    def primary_key(row: dict[str, Any]) -> tuple[Any, ...]:
        if field == "severity":
            sev = row.get("severity")
            ordinal = _SEVERITY_ORDINAL.get(sev, 99)
            return (ordinal,)
        return (_text_sort_key(row.get(field)),)

    indexed = list(enumerate(rows))
    indexed.sort(
        key=lambda pair: (*primary_key(pair[1]), pair[0], pair[1].get("id", "")),
        reverse=reverse,
    )
    return [row for _, row in indexed]
```

Import `QUALITY_SORT_FIELDS` / `QualityQueryError` from `app.bridge_contract` (application may import app contract — match existing `quality_query` → `dto_mapper` pattern; if layer lint blocks, duplicate frozenset in application and validate in `BridgeApi` only — prefer single source in `bridge_contract` + re-export constant in `quality_query`).

- [ ] **Step 3: Map error in `bridge_api.py`**

```python
def query_quality_rows(self, query: dict[str, Any]) -> dict[str, Any]:
    _ = clamp_query_limit(query)
    try:
        payload = self._session.query_quality_rows(query)
    except QualityQueryError as exc:
        raise PreviewApplyError(exc.reason, str(exc)) from exc
    validate_quality_rows_page(payload)
    return payload
```

(`PreviewApplyError` JSON `__str__` is already parsed by TS — reason `INVALID_SORT_FIELD`.)

- [ ] **Step 4: Write failing contract tests**

In `tests/test_bridge_contract.py` add:

```python
def test_query_quality_rows_sort_name_asc(tmp_path: Path) -> None:
    # scan library with 2+ quality issues; query with sort name asc
    # assert row names are non-decreasing by casefold


def test_query_quality_rows_invalid_sort_field_rejected(tmp_path: Path) -> None:
    api = make_api(tmp_path)
    # scan...
    with pytest.raises(PreviewApplyError) as exc:
        api.query_quality_rows({"issueType": "encoding", "sort": {"field": "foo", "direction": "asc"}})
    assert "INVALID_SORT_FIELD" in str(exc.value)


def test_query_quality_rows_stable_sort_tiebreak(tmp_path: Path) -> None:
    # two queries identical sort/filter → same row ids order
```

- [ ] **Step 5: Run pytest**

Run: `pytest tests/test_bridge_contract.py -k "quality_rows_sort or invalid_sort or stable_sort" -v`  
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/app/bridge_contract.py src/application/quality_query.py src/app/bridge_api.py tests/test_bridge_contract.py
git commit -m "[pr27] quality query sort whitelist and stable tie-break"
```

---

### Task 2: mockBridge sort parity

**Files:**
- Modify: `web/src/bridge/mockData.ts`
- Modify: `web/src/bridge/mockBridge.ts`
- Modify: `web/src/bridge/parseBridgeRejection.ts`

- [ ] **Step 1: Add `textSortKey` + `sortQualityRows` in `mockData.ts`**

```typescript
const QUALITY_SORT_FIELDS = new Set([
  "name",
  "path",
  "issueType",
  "severity",
  "encoding",
  "integrity",
]);

const SEVERITY_ORDINAL: Record<string, number> = { error: 0, warning: 1 };

export function textSortKey(value: string | null | undefined): string {
  return (value ?? "").normalize("NFC").toLocaleLowerCase("en-US");
}

export function sortQualityRows(
  rows: QualityRow[],
  sort?: QualityRowsQuery["sort"],
): QualityRow[] {
  if (!sort?.field) return rows;
  if (!QUALITY_SORT_FIELDS.has(sort.field)) {
    throw new BridgeCallError("Bridge call rejected: INVALID_SORT_FIELD", {
      code: "rejected",
      method: "queryQualityRows",
      reason: "INVALID_SORT_FIELD",
    });
  }
  const dir = sort.direction === "desc" ? -1 : 1;
  const field = sort.field;
  const indexed = rows.map((row, index) => ({ row, index }));
  indexed.sort((a, b) => {
    let cmp = 0;
    if (field === "severity") {
      cmp =
        (SEVERITY_ORDINAL[a.row.severity] ?? 99) - (SEVERITY_ORDINAL[b.row.severity] ?? 99);
    } else {
      const av = field === "path" ? a.row.path : (a.row as Record<string, unknown>)[field];
      const bv = field === "path" ? b.row.path : (b.row as Record<string, unknown>)[field];
      cmp = textSortKey(String(av ?? "")).localeCompare(textSortKey(String(bv ?? "")), "en-US");
    }
    if (cmp !== 0) return cmp * dir;
    if (a.index !== b.index) return a.index - b.index;
    return a.row.id.localeCompare(b.row.id);
  });
  return indexed.map((x) => x.row);
}
```

- [ ] **Step 2: Wire sort in `mockBridge.queryQualityRows`**

After `filtered`, before `paginateRows`:

```typescript
const sorted = sortQualityRows(filtered, query.sort);
const { slice, nextCursor, hasMore } = paginateRows(sorted, query.cursor, limit);
// pageInfo.totalFiltered = sorted.length
```

- [ ] **Step 3: Extend `parseBridgeRejection.ts`**

Add `INVALID_SORT_FIELD` to a `QUALITY_QUERY_CODES` list; treat like preview codes when `message` is plain string or JSON `reason`.

- [ ] **Step 4: Run vitest bridge tests**

Run: `cd web && npm run test -- src/bridge/bridgeParity.test.ts`  
Expected: PASS (add tests in Task 3 if not yet present)

- [ ] **Step 5: Commit**

```bash
git add web/src/bridge/mockData.ts web/src/bridge/mockBridge.ts web/src/bridge/parseBridgeRejection.ts
git commit -m "[pr27] mockBridge quality row sort parity"
```

---

### Task 3: TS bridge / query contract tests

**Files:**
- Modify: `web/src/bridge/bridgeParity.test.ts`
- Modify: `tests/test_bridge_contract.py` (Korean fixture if not done in Task 1)

- [ ] **Step 1: mockBridge tests in `bridgeParity.test.ts`**

```typescript
it("queryQualityRows sorts by name asc", async () => {
  const page = await mockBridge.queryQualityRows({
    issueType: "encoding",
    limit: 50,
    sort: { field: "name", direction: "asc" },
  });
  const names = page.rows.map((r) => r.name);
  expect([...names].sort((a, b) => textSortKey(a).localeCompare(textSortKey(b), "en-US"))).toEqual(
    names,
  );
});

it("queryQualityRows rejects invalid sort field", async () => {
  await expect(
    mockBridge.queryQualityRows({
      issueType: "encoding",
      sort: { field: "notAllowed", direction: "asc" },
    }),
  ).rejects.toMatchObject({ reason: "INVALID_SORT_FIELD" });
});

it("queryQualityRows stable order for identical queries", async () => {
  const q = { issueType: "integrity" as const, limit: 20, sort: { field: "severity", direction: "desc" as const } };
  const a = await mockBridge.queryQualityRows(q);
  const b = await mockBridge.queryQualityRows(q);
  expect(a.rows.map((r) => r.id)).toEqual(b.rows.map((r) => r.id));
});
```

- [ ] **Step 2: Python Korean filename fixture (contract)**

Add rows via scan fixtures or inject cache if harness exists; assert mock + python order match for `sort: { field: "name", direction: "asc" }` on names `가.txt`, `나.txt`, `a.txt` — **ASCII + Korean only** per spec §5.3.

- [ ] **Step 3: Run tests**

Run: `pytest tests/test_bridge_contract.py -k quality -q` and `cd web && npm run test -- src/bridge/bridgeParity.test.ts`  
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add web/src/bridge/bridgeParity.test.ts tests/test_bridge_contract.py
git commit -m "[pr27] quality sort contract tests mock and python"
```

---

### Task 4: `qualityGridColumns` + `qualityGridLayout`

**Files:**
- Modify: `web/src/features/work/quality/qualityGridColumns.tsx`
- Create: `web/src/features/work/quality/qualityGridLayout.ts`
- Create: `web/src/features/work/quality/qualityGridPersistence.ts`

- [ ] **Step 1: Storage keys and defaults in `qualityGridColumns.tsx`**

```typescript
export const QUALITY_GRID_COLUMNS_KEY = "novelguard.qualityGrid.columns.v1";
export const QUALITY_GRID_SIZING_KEY = "novelguard.qualityGrid.sizing.v1";

export const OPTIONAL_QUALITY_COLUMN_KEYS = [
  "severity",
  "encoding",
  "integrity",
  "path",
  "issueType",
] as const;

export const qualityGridDefaultVisibility: Record<string, boolean> = {
  name: true,
  severity: true,
  encoding: true,
  integrity: true,
  path: false,
  issueType: false,
};
```

- [ ] **Step 2: Six column defs**

Add accessors for `severity`, `path`, `issueType` with `meta: { gridWidth, minWidthPx, resizable: true }`, `enableSorting: true`. Issue type cell uses short labels map:

```typescript
const ISSUE_TYPE_LABEL: Record<QualityIssueType, string> = {
  integrity: "무결성",
  encoding: "인코딩",
  small_file: "소형",
};
```

- [ ] **Step 3: `qualityGridLayout.ts`**

Mirror `reviewGridLayout.ts` thresholds for six columns (name always survives; path/issueType hide first).

```typescript
const RESPONSIVE_THRESHOLDS: Record<string, number> = {
  severity: 280,
  encoding: 360,
  integrity: 440,
  issueType: 520,
  path: 600,
};

export function mergeQualityColumnVisibility(containerWidth: number): VisibilityState {
  const merged: VisibilityState = { name: true };
  for (const [key, minWidth] of Object.entries(RESPONSIVE_THRESHOLDS)) {
    merged[key] = containerWidth >= 200 && containerWidth >= minWidth;
  }
  return merged;
}
```

- [ ] **Step 4: `qualityGridPersistence.ts`**

```typescript
export function loadQualityColumnVisibility(): Record<string, boolean> {
  try {
    const raw = localStorage.getItem(QUALITY_GRID_COLUMNS_KEY);
    if (!raw) return { ...qualityGridDefaultVisibility };
    const parsed = JSON.parse(raw) as Record<string, boolean>;
    return { ...qualityGridDefaultVisibility, ...parsed, name: true };
  } catch {
    return { ...qualityGridDefaultVisibility };
  }
}

export function saveQualityColumnVisibility(visibility: Record<string, boolean>): void {
  const payload: Record<string, boolean> = {};
  for (const key of OPTIONAL_QUALITY_COLUMN_KEYS) {
    if (visibility[key] !== undefined) payload[key] = visibility[key] !== false;
  }
  localStorage.setItem(QUALITY_GRID_COLUMNS_KEY, JSON.stringify(payload));
}

export function loadQualityColumnSizing(): Record<string, number> { /* same pattern as Resolve */ }
```

- [ ] **Step 5: Commit**

```bash
git add web/src/features/work/quality/
git commit -m "[pr27] quality grid columns layout and persistence helpers"
```

---

### Task 5: `ColumnChooser` (shared component, Quality-only wiring)

**Files:**
- Create: `web/src/components/grid/ColumnChooser.tsx`

- [ ] **Step 1: Implement component** (from PR-12 plan 003)

```tsx
const LABELS: Record<string, string> = {
  severity: "Severity",
  encoding: "Encoding",
  integrity: "Integrity",
  path: "Path",
  issueType: "Type",
};

export function ColumnChooser({
  testId = "grid-column-chooser",
  visibility,
  optionalKeys,
  onChange,
}: {
  testId?: string;
  visibility: VisibilityState;
  optionalKeys: readonly string[];
  onChange: (key: string, visible: boolean) => void;
}) {
  return (
    <details className="relative text-sm" data-testid={testId}>
      <summary className="cursor-pointer list-none rounded-md border border-outline px-3 py-1.5 text-on-surface-variant hover:bg-hover">
        열 선택
      </summary>
      <div className="absolute right-0 z-20 mt-1 min-w-[12rem] rounded-md border border-outline bg-surface-elevated p-2 shadow-lg">
        {optionalKeys.map((key) => (
          <label key={key} className="flex items-center gap-2 py-1">
            <input
              type="checkbox"
              data-testid={`column-toggle-${key}`}
              checked={visibility[key] !== false}
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

**Do not** import or render in `ResolveAndOrganizeWorkspace.tsx` (LOCK-8).

- [ ] **Step 2: Commit**

```bash
git add web/src/components/grid/ColumnChooser.tsx
git commit -m "[pr27] shared ColumnChooser component"
```

---

### Task 6: `VirtualizedQualityGrid` + footer / resize

**Files:**
- Create: `web/src/features/work/quality/VirtualizedQualityGrid.tsx`
- Modify: `web/src/features/work/quality/QualityIssueGrid.tsx`

- [ ] **Step 1: Create wrapper** (copy structure from `VirtualizedReviewGrid.tsx`)

Props include `userColumnVisibility: VisibilityState` and `mergeColumnVisibility` factory:

```typescript
export function VirtualizedQualityGrid({
  rows,
  selectedRowId,
  onSelectRow,
  onNearEnd,
  loadingMore,
  sorting,
  onSortingChange,
  userColumnVisibility,
  columnSizing,
  onColumnSizingChange,
}: { /* ... */ }) {
  const columns = useMemo(() => buildQualityGridColumns(), []);

  const mergeEffectiveVisibility = useCallback(
    (containerWidth: number) => {
      const responsive = mergeQualityColumnVisibility(containerWidth);
      const merged: VisibilityState = { name: true };
      for (const key of ["severity", "encoding", "integrity", "path", "issueType"] as const) {
        merged[key] =
          userColumnVisibility[key] !== false && responsive[key] !== false;
      }
      return merged;
    },
    [userColumnVisibility],
  );

  return (
    <VirtualizedDataGrid
      testId="quality-issue-grid"
      headerTestIdPrefix="quality-grid-header"
      data={rows}
      columns={columns}
      getRowId={(row) => row.id}
      selectedRowId={selectedRowId}
      onSelectRow={onSelectRow}
      sorting={sorting}
      onSortingChange={onSortingChange}
      mergeColumnVisibility={mergeEffectiveVisibility}
      columnSizing={columnSizing}
      onColumnSizingChange={onColumnSizingChange}
      enableColumnResize
      onNearEnd={onNearEnd}
      loadingMore={loadingMore}
      footer={/* loaded rows count — match Review */}
    />
  );
}
```

- [ ] **Step 2: Deprecate fat `QualityIssueGrid`**

Either re-export `VirtualizedQualityGrid` as `QualityIssueGrid` or update workspace import — single public entry.

- [ ] **Step 3: Commit**

```bash
git add web/src/features/work/quality/VirtualizedQualityGrid.tsx web/src/features/work/quality/QualityIssueGrid.tsx
git commit -m "[pr27] VirtualizedQualityGrid wrapper with resize and footer"
```

---

### Task 7: `QualityWorkspace` integration

**Files:**
- Modify: `web/src/features/work/QualityWorkspace.tsx`

- [ ] **Step 1: Add state**

```typescript
import type { SortingState } from "@tanstack/react-table";
const [sorting, setSorting] = useState<SortingState>([]);
const [loading, setLoading] = useState(false);
const [columnVisibility, setColumnVisibility] = useState(loadQualityColumnVisibility);
const [columnSizing, setColumnSizing] = useState(loadQualityColumnSizing);
```

- [ ] **Step 2: `currentQuery` useMemo** (spec §4.2)

Include `sort` from `sorting[0]`; add `sorting` to `loadPage` dependency array.

- [ ] **Step 3: `loadPage` loading flags**

```typescript
if (!append) setLoading(true);
else setLoadingMore(true);
// finally: setLoading(false);
```

- [ ] **Step 4: `libraryRevision` reload**

```typescript
const libraryRevision = snapshot.work.resolve.libraryRevision;
useEffect(() => {
  const frame = requestAnimationFrame(() => void loadPage(null, false));
  return () => cancelAnimationFrame(frame);
}, [libraryRevision, loadPage]);
```

Keep existing `issueType`/`loadPage` effect or merge carefully to avoid double-fetch on mount — prefer **single** effect deps: `[loadPage]` where `loadPage` already depends on `issueType` and `sorting`; add **separate** effect only for `libraryRevision` changes **after** first mount (use ref `initialRevisionSeen` if needed).

- [ ] **Step 5: Render chooser + grid**

```tsx
<ColumnChooser
  testId="quality-column-chooser"
  visibility={columnVisibility}
  optionalKeys={OPTIONAL_QUALITY_COLUMN_KEYS}
  onChange={(key, visible) => {
    setColumnVisibility((prev) => {
      const next = { ...prev, [key]: visible };
      saveQualityColumnVisibility(next);
      return next;
    });
  }}
/>
<VirtualizedQualityGrid
  sorting={sorting}
  onSortingChange={setSorting}
  userColumnVisibility={columnVisibility}
  columnSizing={columnSizing}
  onColumnSizingChange={(next) => {
    setColumnSizing(next);
    localStorage.setItem(QUALITY_GRID_SIZING_KEY, JSON.stringify(next));
  }}
  /* rows, selection, pagination */
/>
{loading && !queryError && (
  <p className="mt-2 text-xs text-muted" data-testid="quality-grid-loading">
    Loading rows…
  </p>
)}
```

- [ ] **Step 6: Manual smoke**

Run: `cd web && npm run dev` → Quality tab → toggle sort, chooser, resize, narrow window.  
Expected: no console errors; query includes `sort`; invalid sort not reachable from UI.

- [ ] **Step 7: Commit**

```bash
git add web/src/features/work/QualityWorkspace.tsx
git commit -m "[pr27] QualityWorkspace sort chooser sizing and revision reload"
```

---

### Task 8: Perf fixture + DOM cap test

**Files:**
- Modify: `web/src/components/grid/VirtualizedDataGrid.test.tsx`

- [ ] **Step 1: Add Quality perf describe block**

```typescript
import { buildQualityGridColumns } from "../../features/work/quality/qualityGridColumns";
import type { QualityRow } from "../../types/quality";

describe("VirtualizedDataGrid quality columns perf", () => {
  it("renders bounded DOM rows for 2000 logical quality rows", () => {
    const data: QualityRow[] = Array.from({ length: 2000 }, (_, i) => ({
      id: `quality:q${i}`,
      issueType: "encoding",
      name: `file-${i}.txt`,
      path: `/lib/file-${i}.txt`,
      encoding: "UTF-8",
      integrity: "Decode error",
      severity: i % 2 === 0 ? "error" : "warning",
    }));
    const { container } = render(
      <div style={{ height: 400, width: 900, display: "flex" }}>
        <VirtualizedDataGrid
          testId="quality-perf-grid"
          data={data}
          columns={buildQualityGridColumns()}
          getRowId={(r) => r.id}
          mergeColumnVisibility={() => ({
            name: true,
            severity: true,
            encoding: true,
            integrity: true,
            path: false,
            issueType: false,
          })}
          overscan={6}
        />
      </div>,
    );
    const domRows = container.querySelectorAll('[data-testid="grid-row"]');
    expect(domRows.length).toBeLessThanOrEqual(maxRenderedRowSlots({ overscan: 6 }));
  });
});
```

- [ ] **Step 2: Run perf suite**

Run: `cd web && npm run test:perf`  
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add web/src/components/grid/VirtualizedDataGrid.test.tsx
git commit -m "[pr27] quality grid perf DOM cap test"
```

---

### Task 9: Smoke / PR-21 regression guards

**Files:**
- Modify: `web/e2e/smoke.spec.ts` (optional)
- Modify: `web/src/bridge/bridgeParity.test.ts` (source scan guard if needed)

- [ ] **Step 1: Extend existing smoke (no new file)**

```typescript
test("quality grid header sort triggers query", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: /품질/i }).click();
  await page.getByTestId("quality-grid-header-name").click();
  // expect first row changes or aria sort indicator — minimal assertion
});

test("quality column chooser persists path column", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: /품질/i }).click();
  await page.getByTestId("quality-column-chooser").click();
  await page.getByTestId("column-toggle-path").check();
  await expect(page.getByTestId("quality-grid-header-path")).toBeVisible();
});
```

Skip if Playwright env not available in agent session — document in completion report.

- [ ] **Step 2: PR-21 regression checklist (manual / existing E2E)**

Confirm still present:

- `quality-detail-stale`, `quality-detail-error`, `quality-repair-open`, `getQualityIssueDetail` flow

- [ ] **Step 3: Commit** (if smoke added)

```bash
git add web/e2e/smoke.spec.ts
git commit -m "[pr27] e2e quality sort and column chooser smoke"
```

---

### Task 10: Final verification + docs status

**Files:**
- Modify: `docs/superpowers/specs/015-2026-06-02-quality-grid-parity-design.md`
- Modify: `docs/superpowers/roadmap/002-2026-06-02-pr26-pr30-platform-polish-roadmap.md`
- Modify: this plan file

- [ ] **Step 1: Full verification**

Run: `python scripts/verify_phase_completion.py`  
Expected: PASS (pytest, ruff, mypy, black, npm lint)

Run: `cd web && npm run test:perf`  
Expected: PASS

- [ ] **Step 2: Update spec 015 status**

```markdown
**Approved** (2026-06-02) — implemented per [plan 021](../plans/021-2026-06-02-pr27-quality-grid-parity.md) (**complete** YYYY-MM-DD).
```

- [ ] **Step 3: Update roadmap PR-27 row**

Status → **Done** with date; check pre-implementation checklist items.

- [ ] **Step 4: Mark plan complete**

`Plan status: **Complete** (YYYY-MM-DD)`

- [ ] **Step 5: Commit docs** (optional separate docs commit)

```bash
git add docs/superpowers/
git commit -m "[pr27] mark PR-27 quality grid parity complete in docs"
```

---

## Spec coverage self-review

| Spec requirement | Task |
|------------------|------|
| LOCK-1 read-only | All tasks (no apply/repair changes) |
| LOCK-2 six columns | Task 4 |
| LOCK-3 no suggestedAction column | Task 4 |
| LOCK-4 sort whitelist | Task 1–3 |
| LOCK-5 parity tests | Task 1, 3 |
| LOCK-6 columns.v1 | Task 4, 7 |
| LOCK-7 sizing.v1 | Task 4, 6–7 |
| LOCK-8 no Resolve chooser | Task 5, 0 freeze |
| LOCK-9–10 | Scope freeze header |
| D7 deterministic sort | Task 1–2 |
| §5.6 tie-break | Task 1–2 |
| A4 perf 2k | Task 8 |
| A6 PR-21 | Task 9 |
| A7 no second poller | Task 7 (revision reload via snapshot only) |
| PR-26 | Task 7 note |

No TBD placeholders in task steps.

---

## Execution handoff

**Plan saved to** `docs/superpowers/plans/021-2026-06-02-pr27-quality-grid-parity.md`.

**Execution options:**

1. **Subagent-driven (recommended)** — fresh subagent per task, review between tasks  
2. **Inline** — `executing-plans` in this session with checkpoints  

**Human gate:** Approve **Task 0** before implementation. Per workflow: commit **spec + plan together** after plan approval if desired (no commit done by agent unless requested).

---

## Changelog

| Date | Change |
|------|--------|
| 2026-06-02 | Initial plan 021 from approved spec 015 + reviewer task structure |
