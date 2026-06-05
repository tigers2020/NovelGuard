# NOV-29: Resolve review-only inline guidance + tab labels — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show persistent `batch-review-only-banner` on Near/Relation/All type filters and rename toolbar tab labels with Korean role hints; preview/bulk disable logic unchanged.

**Architecture:** Add display-only `reviewOnlyGuidanceBannerForFilter()` beside existing `reviewOnlyBlockedReasonForFilter()`; pass guidance string into `BatchActionBar`; update `TYPE_FILTERS` labels only. Workspace wires banner from `rowTypeFilter` — no feedback into eligibility.

**Tech Stack:** React+TS (`web/`), vitest, Playwright e2e.

**Spec:** [2026-06-05-nov-29-review-only-inline-guidance-design.md](../specs/2026-06-05-nov-29-review-only-inline-guidance-design.md)

**Branch:** `ai/NOV-29-resolve-review-only-inline-guidance` from `main`

---

## File map

| File | Responsibility |
|------|----------------|
| `web/src/features/work/resolve/previewEligibility.ts` | `reviewOnlyGuidanceBannerForFilter()` |
| `web/src/features/work/resolve/previewEligibility.test.ts` | Banner strings per filter |
| `web/src/features/work/resolve/BatchActionBar.tsx` | `reviewOnlyGuidance` prop + banner row |
| `web/src/features/work/resolve/BatchActionBar.test.tsx` | Banner visible/hidden |
| `web/src/features/work/resolve/ResolveGridToolbar.tsx` | `TYPE_FILTERS` label rename |
| `web/src/features/work/ResolveAndOrganizeWorkspace.tsx` | Pass guidance prop |
| `web/e2e/smoke.spec.ts` | NOV-29 banner + exact absence |

---

### Task 1: `reviewOnlyGuidanceBannerForFilter`

**Files:**
- Modify: `web/src/features/work/resolve/previewEligibility.ts`
- Test: `web/src/features/work/resolve/previewEligibility.test.ts`

- [ ] **Step 1: Write the failing test**

Add after `reviewOnlyBlockedReasonForFilter` describe block in `previewEligibility.test.ts`:

```typescript
import {
  hasExecutableMovePreviewRows,
  isExecutableMovePreviewRow,
  reviewOnlyBlockedReasonForFilter,
  reviewOnlyGuidanceBannerForFilter,
} from "./previewEligibility";

describe("reviewOnlyGuidanceBannerForFilter", () => {
  it("returns undefined for exact filter", () => {
    expect(reviewOnlyGuidanceBannerForFilter("exact")).toBeUndefined();
  });

  it("returns banner copy for near, relation, and all", () => {
    expect(reviewOnlyGuidanceBannerForFilter("near")).toMatch(
      /Near 중복은 검토 전용/,
    );
    expect(reviewOnlyGuidanceBannerForFilter("near")).toMatch(/Exact \(이동\)/);

    expect(reviewOnlyGuidanceBannerForFilter("relation")).toMatch(
      /Relation 그룹은 검토 전용/,
    );
    expect(reviewOnlyGuidanceBannerForFilter("relation")).toMatch(/Exact \(이동\)/);

    expect(reviewOnlyGuidanceBannerForFilter("all")).toMatch(
      /검토 전용 유형이 포함/,
    );
    expect(reviewOnlyGuidanceBannerForFilter("all")).toMatch(/Exact \(이동\)/);
  });

  it("does not reuse tooltip-only blocked reason strings", () => {
    expect(reviewOnlyGuidanceBannerForFilter("near")).not.toBe(
      reviewOnlyBlockedReasonForFilter("near"),
    );
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd web && npm run test -- src/features/work/resolve/previewEligibility.test.ts -v`  
Expected: FAIL — `reviewOnlyGuidanceBannerForFilter is not a function` or not exported

- [ ] **Step 3: Implement helper**

In `previewEligibility.ts`, after `reviewOnlyBlockedReasonForFilter`:

```typescript
/** Longer inline banner copy for BatchActionBar; tooltips stay on reviewOnlyBlockedReasonForFilter. */
export function reviewOnlyGuidanceBannerForFilter(
  rowTypeFilter: RowTypeFilter,
): string | undefined {
  if (rowTypeFilter === "near") {
    return "Near 중복은 검토 전용입니다. 이동 미리보기·적용은 Exact (이동) 탭에서만 가능합니다.";
  }
  if (rowTypeFilter === "relation") {
    return "Relation 그룹은 검토 전용입니다. 이동 미리보기·적용은 Exact (이동) 탭에서만 가능합니다.";
  }
  if (rowTypeFilter === "all") {
    return "현재 필터에 검토 전용 유형이 포함되어 있습니다. 이동 미리보기는 Exact (이동) 탭을 선택하세요.";
  }
  return undefined;
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd web && npm run test -- src/features/work/resolve/previewEligibility.test.ts -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add web/src/features/work/resolve/previewEligibility.ts web/src/features/work/resolve/previewEligibility.test.ts
git commit -m "feat(web): add review-only guidance banner copy helper (NOV-29)"
```

---

### Task 2: `BatchActionBar` banner row

**Files:**
- Modify: `web/src/features/work/resolve/BatchActionBar.tsx`
- Test: `web/src/features/work/resolve/BatchActionBar.test.tsx`

- [ ] **Step 1: Write the failing tests**

Add to `BatchActionBar.test.tsx`:

```typescript
  it("shows review-only guidance banner when reviewOnlyGuidance is set", () => {
    render(
      <BatchActionBar
        filteredCount={10}
        loadedCount={10}
        reviewOnlyGuidance="Near 중복은 검토 전용입니다. 이동 미리보기·적용은 Exact (이동) 탭에서만 가능합니다."
        onExcludeAllFiltered={noop}
        onPreview={noop}
      />,
    );

    const banner = screen.getByTestId("batch-review-only-banner");
    expect(banner).toHaveAttribute("role", "status");
    expect(banner.textContent).toMatch(/Exact \(이동\)/);
  });

  it("hides review-only banner when reviewOnlyGuidance is undefined", () => {
    render(
      <BatchActionBar
        filteredCount={10}
        loadedCount={10}
        onExcludeAllFiltered={noop}
        onPreview={noop}
      />,
    );

    expect(screen.queryByTestId("batch-review-only-banner")).toBeNull();
  });
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd web && npm run test -- src/features/work/resolve/BatchActionBar.test.tsx -v`  
Expected: FAIL — unknown prop `reviewOnlyGuidance` or missing testid

- [ ] **Step 3: Implement banner**

Update `BatchActionBar.tsx` props and layout:

```typescript
export function BatchActionBar({
  filteredCount,
  loadedCount,
  loadingAll = false,
  reviewOnlyGuidance,
  onExcludeAllFiltered,
  bulkQueryDisabled = false,
  bulkQueryDisabledReason,
  onPreview,
  previewDisabled = false,
  previewDisabledReason,
}: {
  filteredCount: number;
  loadedCount: number;
  loadingAll?: boolean;
  reviewOnlyGuidance?: string;
  onExcludeAllFiltered: () => void;
  bulkQueryDisabled?: boolean;
  bulkQueryDisabledReason?: string;
  onPreview: () => void;
  previewDisabled?: boolean;
  previewDisabledReason?: string;
}) {
  const bulkFilterDisabled = bulkQueryDisabled || filteredCount === 0;

  return (
    <div className="shrink-0 border-t border-outline bg-surface">
      {reviewOnlyGuidance ? (
        <div className="px-4 pt-3">
          <div
            className="rounded-md border border-secondary/40 bg-secondary/10 p-3 text-sm text-on-surface"
            role="status"
            data-testid="batch-review-only-banner"
          >
            {reviewOnlyGuidance}
          </div>
        </div>
      ) : null}
      <div className="relative z-30 flex flex-wrap items-center justify-between gap-3 px-4 py-3">
        {/* existing counts + buttons unchanged */}
      </div>
    </div>
  );
}
```

Keep inner row markup (counts, buttons) identical to current implementation.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd web && npm run test -- src/features/work/resolve/BatchActionBar.test.tsx -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add web/src/features/work/resolve/BatchActionBar.tsx web/src/features/work/resolve/BatchActionBar.test.tsx
git commit -m "feat(web): batch bar review-only guidance banner (NOV-29)"
```

---

### Task 3: Wire workspace + toolbar labels

**Files:**
- Modify: `web/src/features/work/ResolveAndOrganizeWorkspace.tsx`
- Modify: `web/src/features/work/resolve/ResolveGridToolbar.tsx`

- [ ] **Step 1: Update toolbar labels**

In `ResolveGridToolbar.tsx`, change `TYPE_FILTERS`:

```typescript
const TYPE_FILTERS: { id: ResolveRowTypeFilter; label: string }[] = [
  { id: "exact", label: "Exact (이동)" },
  { id: "near", label: "Near (참고)" },
  { id: "relation", label: "Relation (참고)" },
  { id: "all", label: "All types" },
];
```

- [ ] **Step 2: Wire guidance in workspace**

In `ResolveAndOrganizeWorkspace.tsx`, extend import:

```typescript
import {
  hasExecutableMovePreviewRows,
  reviewOnlyBlockedReasonForFilter,
  reviewOnlyGuidanceBannerForFilter,
} from "./resolve/previewEligibility";
```

Add memo after `reviewOnlyBlockedReason`:

```typescript
  const reviewOnlyGuidance = useMemo(
    () => reviewOnlyGuidanceBannerForFilter(rowTypeFilter),
    [rowTypeFilter],
  );
```

Pass to `BatchActionBar`:

```typescript
      <BatchActionBar
        filteredCount={filteredCount}
        loadedCount={rows.length}
        loadingAll={loadingAll}
        reviewOnlyGuidance={reviewOnlyGuidance}
        onExcludeAllFiltered={() => setBulkExcludeConfirmOpen(true)}
        bulkQueryDisabled={Boolean(reviewOnlyBlockedReason)}
        bulkQueryDisabledReason={reviewOnlyBlockedReason}
        onPreview={() => onOpenPreview(previewSelection)}
        previewDisabled={Boolean(previewBlockedReason)}
        previewDisabledReason={previewBlockedReason}
      />
```

Do **not** change `previewBlockedReason` or `bulkQueryDisabled` logic.

- [ ] **Step 3: Run unit tests**

Run: `cd web && npm run test -- src/features/work/resolve/previewEligibility.test.ts src/features/work/resolve/BatchActionBar.test.tsx -v`  
Expected: PASS

- [ ] **Step 4: Run lint**

Run: `cd web && npm run lint`  
Expected: exit 0

- [ ] **Step 5: Commit**

```bash
git add web/src/features/work/ResolveAndOrganizeWorkspace.tsx web/src/features/work/resolve/ResolveGridToolbar.tsx
git commit -m "feat(web): wire review-only banner and rename type filter labels (NOV-29)"
```

---

### Task 4: E2E — NOV-29 banner visibility

**Files:**
- Modify: `web/e2e/smoke.spec.ts`

- [ ] **Step 1: Add E2E test after NOV-22 block (~line 291)**

```typescript
  test("NOV-29 review-only banner visible on near/all and hidden on exact", async ({ page }) => {
    await openResolveWorkspace(page);

    await expect(page.getByTestId("batch-review-only-banner")).toHaveCount(0);

    await page.getByTestId("resolve-type-filter-near").click();
    const nearBanner = page.getByTestId("batch-review-only-banner");
    await expect(nearBanner).toBeVisible();
    await expect(nearBanner).toContainText("Exact (이동)");
    await expect(page.getByTestId("batch-preview-open")).toBeDisabled();

    await page.getByTestId("resolve-type-filter-all").click();
    await expect(page.getByTestId("batch-review-only-banner")).toBeVisible();
    await expect(page.getByTestId("batch-preview-open")).toBeDisabled();

    await page.getByTestId("resolve-type-filter-exact").click();
    await expect(page.getByTestId("batch-review-only-banner")).toHaveCount(0);
  });
```

- [ ] **Step 2: Run E2E**

Run: `cd web && npm run test:e2e -- e2e/smoke.spec.ts -g "NOV-29"`  
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add web/e2e/smoke.spec.ts
git commit -m "test(e2e): assert review-only batch banner on type filters (NOV-29)"
```

---

### Task 5: Final verification

- [ ] **Step 1: Run combined unit tests**

Run: `cd web && npm run test -- src/features/work/resolve/previewEligibility.test.ts src/features/work/resolve/BatchActionBar.test.tsx -v`  
Expected: PASS

- [ ] **Step 2: Confirm NOV-19/22 preview-disable tests still pass**

Run: `cd web && npm run test:e2e -- e2e/smoke.spec.ts -g "NOV-19|NOV-22"`  
Expected: PASS — no regression on disabled preview + tooltips
