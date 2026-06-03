# Work Layout Pane Hierarchy (Minimal) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Spec:** [029 pane hierarchy minimal](../specs/029-2026-06-03-feature-ui-layout-pane-hierarchy-minimal-design.md) (**approved** 2026-06-03)

**Goal:** Reclaim Resolve/Quality vertical space via dock auto-collapse on non-Scan modes and move Resolve hero chrome into a compact grid toolbar inside the 3-pane body.

**Architecture:** Pure policy helpers + `WorkRoute.onWorkModeApplied` / `handleOpenResolve` collapse (no effect); `ResolveGridToolbar` in center pane; no `AppShell` or bridge changes.

**Plan status:** Done (2026-06-03)

**Tech Stack:** React 19, TypeScript, Tailwind v4, Vitest, Playwright

**Test policy:** Extend existing tests only — no new test files.

---

## File map

| File | Action |
|------|--------|
| `web/src/components/layout/shellFileDockModePolicy.ts` | Create — pure collapse policy |
| `web/src/app/App.tsx` | Modify — wire effect on `activeMode` |
| `web/src/features/work/resolve/ResolveGridToolbar.tsx` | Create — compact toolbar UI |
| `web/src/features/work/ResolveAndOrganizeWorkspace.tsx` | Modify — remove hero, mount toolbar in center pane |
| `web/src/bridge/bridgeParity.test.ts` | Modify — unit tests for policy |
| `web/e2e/smoke.spec.ts` | Modify — dock collapsed on Resolve + Scan return behavior |

---

### Task 1: Shell file dock mode policy

**Files:**
- Create: `web/src/components/layout/shellFileDockModePolicy.ts`
- Modify: `web/src/bridge/bridgeParity.test.ts`

- [ ] **Step 1: Write the failing test**

Add to `web/src/bridge/bridgeParity.test.ts`:

```typescript
import { shouldCollapseFileDockForWorkMode } from "../components/layout/shellFileDockModePolicy";

describe("shouldCollapseFileDockForWorkMode", () => {
  it("returns true for resolve and quality", () => {
    expect(shouldCollapseFileDockForWorkMode("resolve")).toBe(true);
    expect(shouldCollapseFileDockForWorkMode("quality")).toBe(true);
  });

  it("returns false for scan", () => {
    expect(shouldCollapseFileDockForWorkMode("scan")).toBe(false);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd web && npm run test -- src/bridge/bridgeParity.test.ts -t shouldCollapseFileDockForWorkMode`

Expected: FAIL — module not found

- [ ] **Step 3: Implement policy**

Create `web/src/components/layout/shellFileDockModePolicy.ts`:

```typescript
import type { WorkMode } from "../../types/snapshot";

/** LOCK-LAYOUT-2: collapse dock when entering Resolve or Quality. */
export function shouldCollapseFileDockForWorkMode(mode: WorkMode): boolean {
  return mode === "resolve" || mode === "quality";
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd web && npm run test -- src/bridge/bridgeParity.test.ts -t shouldCollapseFileDockForWorkMode`

Expected: PASS

---

### Task 2: Auto-collapse in App

**Files:**
- Modify: `web/src/app/App.tsx`

- [ ] **Step 1: Add effect on activeMode**

Import `shouldCollapseFileDockForWorkMode` and add after state declarations in `AppContent`:

```typescript
useEffect(() => {
  const mode = snapshot.work.activeMode;
  if (!shouldCollapseFileDockForWorkMode(mode)) {
    return;
  }
  setFileDockExpanded((wasExpanded) => {
    if (!wasExpanded) {
      return wasExpanded;
    }
    persistShellFileDockState({ ...loadShellFileDockState(), expanded: false });
    return false;
  });
}, [snapshot.work.activeMode]);
```

Notes:
- Runs on mount when persisted mode is `resolve`/`quality` with expanded dock — intentional.
- Does **not** re-run when user manually re-expands on Resolve (mode unchanged).
- Persists `expanded: false` — resets Scan expanded preference (LOCK-LAYOUT-2 MVP).

- [ ] **Step 2: Manual smoke**

Run: `cd web && npm run dev:e2e`

1. Scan tab → expand file dock → switch to Resolve → dock collapsed.
2. Switch back to Scan → dock stays collapsed (MVP accepted).

---

### Task 3: ResolveGridToolbar component

**Files:**
- Create: `web/src/features/work/resolve/ResolveGridToolbar.tsx`
- Modify: `web/src/features/work/ResolveAndOrganizeWorkspace.tsx`

- [ ] **Step 1: Create toolbar component**

Extract hero JSX (lines ~302–368) into `ResolveGridToolbar` with props:

```typescript
export type ResolveGridToolbarProps = {
  queueCount: number;
  groupCount: number;
  conflictCount: number;
  approvedCount: number;
  rowTypeFilter: "exact" | "near" | "relation" | "all";
  onRowTypeFilterChange: (id: ResolveGridToolbarProps["rowTypeFilter"]) => void;
  search: string;
  onSearchChange: (value: string) => void;
  loading: boolean;
  queryError: string | null;
  onRetry: () => void;
  onOpenFinalize: () => void;
};
```

Layout classes (compact, 1–2 rows):
- Outer: `shrink-0 border-b border-outline bg-surface px-3 py-2`
- Row 1: `flex flex-wrap items-center gap-2` — optional short title + inline `StatChip`s + `resolve-open-finalize`
- Row 2: `flex flex-wrap items-center gap-2` — `data-testid="resolve-type-filter"` pills + flex-1 search input
- Preserve all existing `data-testid`s from hero block

- [ ] **Step 2: Rewire ResolveAndOrganizeWorkspace**

Remove the top `<div className="shrink-0 border-b border-outline p-4">` hero block entirely.

Structure:

```tsx
<main data-testid="resolve-workspace" className="flex h-full min-h-0 flex-col overflow-hidden ...">
  <div className="relative z-0 flex min-h-0 min-w-0 flex-1 overflow-hidden">
    <FacetPanel ... />
    <div className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden">
      {/* mobile detail strip unchanged */}
      <ResolveGridToolbar ... />
      <VirtualizedReviewGrid ... />  {/* min-h-0 flex-1 via wrapper or grid root */}
    </div>
    {isWideLayout && <DetailPanel ... />}
  </div>
  <BatchActionBar ... />
</main>
```

Ensure `VirtualizedReviewGrid` parent has `min-h-0 flex-1` so grid receives remaining height.

- [ ] **Step 3: Lint**

Run: `cd web && npm run lint`

Expected: 0 errors

---

### Task 4: E2E smoke updates

**Files:**
- Modify: `web/e2e/smoke.spec.ts`

- [ ] **Step 1: Add dock collapse assertion on Resolve entry**

In `openResolveWorkspace` or a dedicated test, after clicking `work-mode-tab-resolve`:

```typescript
await expect(page.getByTestId("shell-file-dock")).toHaveAttribute("data-state", "collapsed");
await expect(page.getByTestId("resolve-review-grid")).toBeVisible({ timeout: 15_000 });
```

- [ ] **Step 2: Add Scan return MVP test**

New test (or extend mode tabs test):

```typescript
test("PR-46 dock collapses on Resolve entry; Scan return stays collapsed (MVP)", async ({ page }) => {
  await page.goto("/");
  await page.getByTestId("work-mode-tab-scan").click();
  await page.getByTestId("shell-file-dock").getByRole("button", { name: /파일 목록/ }).click();
  await expect(page.getByTestId("shell-file-dock")).toHaveAttribute("data-state", "expanded");
  await page.getByTestId("work-mode-tab-resolve").click();
  await expect(page.getByTestId("shell-file-dock")).toHaveAttribute("data-state", "collapsed");
  await page.getByTestId("work-mode-tab-scan").click();
  await expect(page.getByTestId("shell-file-dock")).toHaveAttribute("data-state", "collapsed");
});
```

Adjust PR label in test name to match your PR id if different.

- [ ] **Step 3: Run e2e**

Run: `cd web && npm run test:e2e -- --grep "dock collapses"`

Expected: PASS

---

### Task 5: Final verification

- [ ] **Step 1: Unit tests**

Run: `cd web && npm run test`

Expected: all pass

- [ ] **Step 2: Lint**

Run: `cd web && npm run lint`

Expected: 0 errors

- [ ] **Step 3: Spec acceptance checklist**

Verify against [029](../specs/029-2026-06-03-feature-ui-layout-pane-hierarchy-minimal-design.md) acceptance criteria — all boxes checked.

---

## Plan self-review (spec coverage)

| Spec requirement | Task |
|------------------|------|
| LOCK-LAYOUT-1 primary table policy | No code change — documentation only |
| LOCK-LAYOUT-2 auto-collapse + persistence reset | Task 1, 2 |
| LOCK-LAYOUT-3 3-pane + toolbar | Task 3 |
| LOCK-LAYOUT-4 terminology | No rename |
| Scan return no auto-expand | Task 2 manual + Task 4 e2e |
| No bridge/Python changes | — |
| Preserve data-testids | Task 3 |

No placeholders remain.

---

## Verification log

| Command | Status | Date |
|---------|--------|------|
| `npm run lint` | PASS (0 errors) | 2026-06-03 |
| `npm run test` | PASS 94 | 2026-06-03 |
| `npm run test:e2e -- --grep "029 dock\|Work mode tabs"` | PASS 3 | 2026-06-03 |
