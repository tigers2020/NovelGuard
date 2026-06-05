# NOV-30: Resolve primary move preview CTA — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a primary move-preview CTA in `ResolveGridToolbar` for Exact filter with executable rows; reuse existing `onOpenPreview` / `ApplySubflowDialog`; demote batch bar preview to outline.

**Architecture:** New `previewCtaCopy.ts` + `countExecutableMovePreviewRows()` in `previewEligibility.ts`; workspace computes label/disabled/show from existing `previewBlockedReason`; toolbar renders primary button beside finalize; batch bar keeps `batch-preview-open` with outline styling.

**Tech Stack:** React+TS (`web/`), vitest, Playwright e2e.

**Spec:** [2026-06-05-nov-30-primary-move-preview-cta-design.md](../specs/2026-06-05-nov-30-primary-move-preview-cta-design.md)

**Branch:** `ai/NOV-30-primary-move-preview-cta` from `main`

---

## File map

| File | Responsibility |
|------|----------------|
| `web/src/features/work/resolve/previewCtaCopy.ts` | Allowed KO labels + forbidden guard |
| `web/src/features/work/resolve/previewCtaCopy.test.ts` | Label variants + forbidden absent |
| `web/src/features/work/resolve/previewEligibility.ts` | `countExecutableMovePreviewRows()` |
| `web/src/features/work/resolve/previewEligibility.test.ts` | Count helper tests |
| `web/src/features/work/resolve/ResolveGridToolbar.tsx` | Primary CTA + props |
| `web/src/features/work/ResolveAndOrganizeWorkspace.tsx` | Wire toolbar props |
| `web/src/features/work/resolve/BatchActionBar.tsx` | Outline preview button + optional `previewLabel` |
| `web/e2e/smoke.spec.ts` | NOV-30 E2E |

---

### Task 1: `countExecutableMovePreviewRows`

**Files:**
- Modify: `web/src/features/work/resolve/previewEligibility.ts`
- Test: `web/src/features/work/resolve/previewEligibility.test.ts`

- [ ] **Step 1: Write the failing test**

Add to `previewEligibility.test.ts`:

```typescript
import {
  countExecutableMovePreviewRows,
  hasExecutableMovePreviewRows,
  isExecutableMovePreviewRow,
  reviewOnlyBlockedReasonForFilter,
} from "./previewEligibility";

describe("countExecutableMovePreviewRows", () => {
  it("counts only executable move_duplicate file rows", () => {
    expect(
      countExecutableMovePreviewRows([
        fileRow({ id: "a", proposedAction: "keep" }),
        fileRow({ id: "b", proposedAction: "move_duplicate" }),
        fileRow({ id: "c", proposedAction: "move_duplicate" }),
        fileRow({ id: "d", status: "excluded", proposedAction: "move_duplicate" }),
      ]),
    ).toBe(2);
  });

  it("returns 0 for empty rows", () => {
    expect(countExecutableMovePreviewRows([])).toBe(0);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd web && npx vitest run src/features/work/resolve/previewEligibility.test.ts -v`  
Expected: FAIL — `countExecutableMovePreviewRows is not defined`

- [ ] **Step 3: Implement helper**

In `previewEligibility.ts`, after `hasExecutableMovePreviewRows`:

```typescript
export function countExecutableMovePreviewRows(rows: readonly ReviewRow[]): number {
  return rows.filter(isExecutableMovePreviewRow).length;
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd web && npx vitest run src/features/work/resolve/previewEligibility.test.ts -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add web/src/features/work/resolve/previewEligibility.ts web/src/features/work/resolve/previewEligibility.test.ts
git commit -m "feat(web): count executable move preview rows (NOV-30)"
```

---

### Task 2: `previewCtaCopy` helper

**Files:**
- Create: `web/src/features/work/resolve/previewCtaCopy.ts`
- Create: `web/src/features/work/resolve/previewCtaCopy.test.ts`

- [ ] **Step 1: Write the failing test**

Create `previewCtaCopy.test.ts`:

```typescript
import { describe, expect, it } from "vitest";
import { previewCtaLabel, FORBIDDEN_PREVIEW_CTA_PHRASES } from "./previewCtaCopy";

describe("previewCtaLabel", () => {
  it("returns Exact N건 label when exact filter and count > 0", () => {
    expect(previewCtaLabel({ filter: "exact", executableCount: 3 })).toBe(
      "Exact 3건 이동 계획 미리보기",
    );
  });

  it("prefers moveReadyCount over executableCount when both set", () => {
    expect(
      previewCtaLabel({ filter: "exact", executableCount: 1, moveReadyCount: 5 }),
    ).toBe("Exact 5건 이동 계획 미리보기");
  });

  it("returns Exact 중복 label when exact filter and count is 0", () => {
    expect(previewCtaLabel({ filter: "exact", executableCount: 0 })).toBe(
      "Exact 중복 이동 계획 미리보기",
    );
  });

  it("returns default label for non-exact filters (batch bar fallback)", () => {
    expect(previewCtaLabel({ filter: "near" })).toBe("이동 계획 미리보기");
  });

  it("never emits forbidden apply-ish phrases", () => {
    const filters = ["exact", "near", "relation", "all"] as const;
    for (const filter of filters) {
      for (const count of [0, 1, 42]) {
        const label = previewCtaLabel({ filter, executableCount: count });
        for (const phrase of FORBIDDEN_PREVIEW_CTA_PHRASES) {
          expect(label).not.toContain(phrase);
        }
      }
    }
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd web && npx vitest run src/features/work/resolve/previewCtaCopy.test.ts -v`  
Expected: FAIL — module not found

- [ ] **Step 3: Implement helper**

Create `previewCtaCopy.ts`:

```typescript
import type { RowTypeFilter } from "./previewEligibility";

export const FORBIDDEN_PREVIEW_CTA_PHRASES = [
  "자동 정리 시작",
  "중복 파일 처리",
  "바로 이동",
] as const;

export type PreviewCtaLabelInput = {
  filter: RowTypeFilter;
  executableCount?: number;
  /** Snapshot count when NOV-27 lands; takes precedence over executableCount. */
  moveReadyCount?: number;
};

export function previewCtaLabel({
  filter,
  executableCount = 0,
  moveReadyCount,
}: PreviewCtaLabelInput): string {
  const n = moveReadyCount ?? executableCount;
  if (filter === "exact" && n > 0) {
    return `Exact ${n}건 이동 계획 미리보기`;
  }
  if (filter === "exact") {
    return "Exact 중복 이동 계획 미리보기";
  }
  return "이동 계획 미리보기";
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd web && npx vitest run src/features/work/resolve/previewCtaCopy.test.ts -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add web/src/features/work/resolve/previewCtaCopy.ts web/src/features/work/resolve/previewCtaCopy.test.ts
git commit -m "feat(web): preview CTA copy helper with forbidden guard (NOV-30)"
```

---

### Task 3: `ResolveGridToolbar` primary CTA

**Files:**
- Modify: `web/src/features/work/resolve/ResolveGridToolbar.tsx`

- [ ] **Step 1: Add props and primary button**

Update component signature and row-1 actions:

```tsx
export function ResolveGridToolbar({
  queueCount,
  groupCount,
  conflictCount,
  approvedCount,
  rowTypeFilter,
  onRowTypeFilterChange,
  search,
  onSearchChange,
  loading,
  queryError,
  onRetry,
  onOpenFinalize,
  showPreviewCta = false,
  onPreview,
  previewDisabled = false,
  previewDisabledReason,
  previewLabel = "이동 계획 미리보기",
}: {
  queueCount: number;
  groupCount: number;
  conflictCount: number;
  approvedCount: number;
  rowTypeFilter: ResolveRowTypeFilter;
  onRowTypeFilterChange: (id: ResolveRowTypeFilter) => void;
  search: string;
  onSearchChange: (value: string) => void;
  loading: boolean;
  queryError: string | null;
  onRetry: () => void;
  onOpenFinalize: () => void;
  showPreviewCta?: boolean;
  onPreview?: () => void;
  previewDisabled?: boolean;
  previewDisabledReason?: string;
  previewLabel?: string;
}) {
```

Replace the lone finalize button block with:

```tsx
        <div className="ml-auto flex flex-wrap items-center gap-2">
          {showPreviewCta && onPreview && (
            <button
              type="button"
              data-testid="resolve-preview-primary"
              disabled={previewDisabled}
              title={previewDisabledReason}
              onClick={onPreview}
              className="rounded-md bg-primary px-3 py-1.5 text-xs font-semibold text-background hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {previewLabel}
            </button>
          )}
          <button
            type="button"
            data-testid="resolve-open-finalize"
            className="rounded-md border border-outline px-3 py-1.5 text-xs font-semibold text-on-surface hover:bg-hover"
            onClick={onOpenFinalize}
          >
            최종 검증
          </button>
        </div>
```

- [ ] **Step 2: Lint**

Run: `cd web && npm run lint`  
Expected: PASS (no new errors in toolbar file)

- [ ] **Step 3: Commit**

```bash
git add web/src/features/work/resolve/ResolveGridToolbar.tsx
git commit -m "feat(web): primary resolve preview CTA in toolbar (NOV-30)"
```

---

### Task 4: Wire workspace + demote batch bar

**Files:**
- Modify: `web/src/features/work/ResolveAndOrganizeWorkspace.tsx`
- Modify: `web/src/features/work/resolve/BatchActionBar.tsx`

- [ ] **Step 1: Import helpers in workspace**

At top of `ResolveAndOrganizeWorkspace.tsx`:

```typescript
import { countExecutableMovePreviewRows } from "./resolve/previewEligibility";
import { previewCtaLabel } from "./resolve/previewCtaCopy";
```

- [ ] **Step 2: Compute toolbar preview props**

After `previewBlockedReason` useMemo, add:

```typescript
  const executableCount = useMemo(
    () => countExecutableMovePreviewRows(rows),
    [rows],
  );

  const previewCtaText = useMemo(
    () =>
      previewCtaLabel({
        filter: rowTypeFilter,
        executableCount,
        // moveReadyCount: resolve.moveReadyCount — wire when NOV-27 merges
      }),
    [rowTypeFilter, executableCount],
  );

  const showPreviewCta = rowTypeFilter === "exact";
```

- [ ] **Step 3: Pass props to `ResolveGridToolbar`**

```tsx
          <ResolveGridToolbar
            queueCount={resolve.queueCount}
            groupCount={resolve.groupCount}
            conflictCount={resolve.conflictCount}
            approvedCount={resolve.approvedCount}
            rowTypeFilter={rowTypeFilter}
            onRowTypeFilterChange={setRowTypeFilter}
            search={search}
            onSearchChange={setSearch}
            loading={loading}
            queryError={queryError}
            onRetry={() => void loadAllFiltered()}
            onOpenFinalize={onOpenFinalize}
            showPreviewCta={showPreviewCta}
            onPreview={() => onOpenPreview(previewSelection)}
            previewDisabled={Boolean(previewBlockedReason)}
            previewDisabledReason={previewBlockedReason}
            previewLabel={previewCtaText}
          />
```

- [ ] **Step 4: Batch bar outline + shared label**

In `BatchActionBar.tsx`, add optional `previewLabel` prop (default `이동 계획 미리보기`) and change preview button class:

```tsx
  previewLabel = "이동 계획 미리보기",
}: {
  // ...existing props...
  previewLabel?: string;
}) {
```

Button:

```tsx
        <button
          type="button"
          disabled={previewDisabled}
          title={previewDisabledReason}
          data-testid="batch-preview-open"
          onClick={onPreview}
          className="rounded-md border border-outline px-3 py-2 text-sm font-semibold text-on-surface hover:bg-hover disabled:cursor-not-allowed disabled:opacity-50"
        >
          {previewLabel}
        </button>
```

In workspace `BatchActionBar`:

```tsx
        previewLabel={previewCtaText}
```

- [ ] **Step 5: Run unit tests**

Run: `cd web && npx vitest run src/features/work/resolve/previewCtaCopy.test.ts src/features/work/resolve/previewEligibility.test.ts -v`  
Expected: PASS

- [ ] **Step 6: Lint**

Run: `cd web && npm run lint`  
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add web/src/features/work/ResolveAndOrganizeWorkspace.tsx web/src/features/work/resolve/BatchActionBar.tsx
git commit -m "feat(web): wire primary preview CTA and outline batch preview (NOV-30)"
```

---

### Task 5: E2E NOV-30

**Files:**
- Modify: `web/e2e/smoke.spec.ts`

- [ ] **Step 1: Add helper for primary CTA click**

After `openApplyDialog`, add:

```typescript
async function openApplyDialogFromToolbar(page: import("@playwright/test").Page) {
  await page
    .getByTestId("resolve-preview-primary")
    .evaluate((el) => (el as HTMLButtonElement).click());
  const dialog = page.getByTestId("apply-subflow-dialog");
  await expect(dialog).toBeVisible();
  await expect(dialog.getByTestId("apply-preview-run")).toBeVisible();
}
```

- [ ] **Step 2: Add NOV-30 test**

```typescript
  test("NOV-30 primary toolbar preview CTA opens apply dialog on exact filter", async ({
    page,
  }) => {
    await openResolveWorkspace(page);
    await prepareExecutableMoveFilter(page);
    const primary = page.getByTestId("resolve-preview-primary");
    await expect(primary).toBeVisible();
    await expect(primary).toBeEnabled();
    await expect(primary).toContainText(/Exact/);
    await openApplyDialogFromToolbar(page);
  });

  test("NOV-30 primary preview CTA hidden on near filter", async ({ page }) => {
    await openResolveWorkspace(page);
    await page.getByTestId("resolve-type-filter-near").click();
    await expect(page.getByTestId("resolve-preview-primary")).toHaveCount(0);
    const batchPreview = page.getByTestId("batch-preview-open");
    await expect(batchPreview).toBeDisabled();
  });
```

- [ ] **Step 3: Run E2E**

Run: `cd web && npm run test:e2e -- --grep "NOV-30"`  
Expected: PASS

- [ ] **Step 4: Contracts**

Run: `cd web && npm run test:contracts`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add web/e2e/smoke.spec.ts
git commit -m "test(e2e): NOV-30 primary resolve preview CTA"
```

---

## Grill-me resolution (locked for implement)

| Decision | Resolution |
|----------|------------|
| Review-only filters | Hide toolbar CTA (`showPreviewCta=false`); batch bar stays disabled with existing title |
| Label when N=0 on exact | `Exact 중복 이동 계획 미리보기` (not generic default) |
| N source until NOV-27 | `countExecutableMovePreviewRows(rows)` only |
| Dual CTAs | Toolbar `bg-primary`; batch `border border-outline` outline |
| Click path | Same `onOpenPreview(previewSelection)` as batch bar |

---

## Final verification

```bash
cd web && npx vitest run src/features/work/resolve/previewCtaCopy.test.ts src/features/work/resolve/previewEligibility.test.ts
cd web && npm run lint
cd web && npm run test:contracts
cd web && npm run test:e2e -- --grep "NOV-30"
```
