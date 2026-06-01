# PR-11: E2E Smoke + Bridge Failure Handling Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prove the React Work UI survives bridge failures (no silent mock fallback in pywebview), surfaces degraded/error states, and passes 5–7 Playwright smoke tests for load, mode tabs, and failure paths.

**Architecture:** Introduce a thin bridge transport layer (`callBridge` + `BridgeCallError`) and `BridgeHealth` state in `SnapshotProvider`. `createPywebviewBridge` stops masking failures with `mockBridge`. UI components show explicit error/retry/degraded affordances. Playwright drives `vite dev` with `window.__NOVELGUARD_TEST_BRIDGE__` injection — no Python host required for CI smoke.

**Tech Stack:** React 19, TypeScript 6, Vitest 3 (unchanged), Playwright 1.49+, Vite 8, existing `mockBridge` / contract validators from PR-10.

**Spec reference:** `docs/superpowers/specs/2026-06-01-novelguard-ui-overhaul-design.md` — GlobalCommandBar, destructive preview→confirm→apply, bridge layering.

**Depends on:** PR-10 complete (`web/src/contracts/*`, `src/app/bridge_contract.py`, Vitest contract tests).

**Testing permission:**

```text
TEST_ALLOWED — Playwright E2E specs under web/e2e/ are explicitly allowed for PR-11.

Rationale:
PR-11 acceptance requires automated smoke for bridge failure paths; contract Vitest tests do not cover DOM behavior.
Limit: web/e2e/*.spec.ts only; no new Python test files unless fixing regressions in existing tests.
```

**Non-goals (PR-11):** Performance benchmark (PR-12), preview-token/stale-apply invariants (PR-13), packaging/webview_main prod path (PR-14), new Work screens, AG Grid, FileDock, repair/finalize, changing contract validators from PR-10.

---

## File map

| File | Responsibility |
|------|----------------|
| `web/playwright.config.ts` | Dev server, Chromium, `baseURL` |
| `web/package.json` | `@playwright/test`, `test:e2e` script |
| `web/src/bridge/bridgeErrors.ts` | `BridgeCallError`, error codes |
| `web/src/bridge/callBridge.ts` | Timeout wrapper, rethrow |
| `web/src/bridge/pywebviewBridge.ts` | Remove silent mock fallback; use `callBridge` |
| `web/src/bridge/testBridge.ts` | Deterministic failing/slow bridges for E2E |
| `web/src/bridge/bridgeHealth.ts` | `BridgeHealth` type + connection label helper |
| `web/src/app/providers/SnapshotProvider.tsx` | Health state, snapshot poll errors, test bridge hook |
| `web/src/components/layout/AppHeader.tsx` | ok / degraded / error connection badge |
| `web/src/features/work/ResolveAndOrganizeWorkspace.tsx` | Query error row + retry |
| `web/src/features/work/ApplySubflowDialog.tsx` | Preview error; apply disabled until preview ok |
| `web/src/features/work/WorkModeTabs.tsx` | `data-testid` on tabs |
| `web/src/features/work/resolve/BatchActionBar.tsx` | `data-testid` on preview button |
| `web/e2e/smoke.spec.ts` | 5–7 Playwright smoke tests |
| `web/e2e/helpers/injectBridge.ts` | `addInitScript` helper |
| `docs/entry_points.md` | E2E run commands |

---

## Acceptance criteria

```text
✓ npm run build pass
✓ npm run test:contracts pass (PR-10 regression)
✓ npm run test:e2e pass (5–7 tests)
✓ pywebview adapter does NOT silently fall back to mockBridge on rejection
✓ queryReviewRows failure shows error UI + retry; grid does not white-screen
✓ getSnapshot timeout/slow failure sets connection to degraded (AppHeader)
✓ getMovePreview failure shows error in ApplySubflowDialog; apply button not offered
✓ Browser dev (no pywebview) still uses mockBridge unchanged
✓ PR-12..14 scope not touched
```

---

### Task 1: Playwright setup

**Files:**
- Modify: `web/package.json`
- Create: `web/playwright.config.ts`

- [ ] **Step 1: Add devDependency and script**

In `web/package.json` `devDependencies`:

```json
"@playwright/test": "^1.49.1"
```

Scripts:

```json
"test:e2e": "playwright test",
"test:e2e:ui": "playwright test --ui"
```

- [ ] **Step 2: Create Playwright config**

Create `web/playwright.config.ts`:

```typescript
import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: "list",
  use: {
    baseURL: "http://127.0.0.1:5173",
    trace: "on-first-retry",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: {
    command: "npm run dev",
    url: "http://127.0.0.1:5173",
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
});
```

- [ ] **Step 3: Install browsers and smoke-run empty suite**

```bash
cd web
npm install
npx playwright install chromium
mkdir e2e
```

Create placeholder `web/e2e/.gitkeep` if needed, then:

```bash
npx playwright test --list
```

Expected: 0 tests or empty list without error.

- [ ] **Step 4: Commit**

```bash
git add web/package.json web/package-lock.json web/playwright.config.ts
git commit -m "[web] add Playwright for PR-11 E2E smoke"
```

---

### Task 2: Bridge errors and `callBridge`

**Files:**
- Create: `web/src/bridge/bridgeErrors.ts`
- Create: `web/src/bridge/callBridge.ts`
- Create: `web/src/bridge/callBridge.test.ts`

- [ ] **Step 1: Write failing Vitest**

Create `web/src/bridge/callBridge.test.ts`:

```typescript
import { describe, expect, it } from "vitest";
import { BridgeCallError } from "./bridgeErrors";
import { callBridge } from "./callBridge";

describe("callBridge", () => {
  it("resolves successful promises", async () => {
    await expect(callBridge(() => Promise.resolve(42), { method: "test" })).resolves.toBe(42);
  });

  it("wraps rejection in BridgeCallError", async () => {
    await expect(
      callBridge(() => Promise.reject(new Error("boom")), { method: "get_snapshot", timeoutMs: 50 }),
    ).rejects.toBeInstanceOf(BridgeCallError);
  });

  it("times out slow calls", async () => {
    await expect(
      callBridge(
        () => new Promise((resolve) => setTimeout(() => resolve(1), 500)),
        { method: "get_snapshot", timeoutMs: 30 },
      ),
    ).rejects.toMatchObject({ code: "timeout" });
  });
});
```

- [ ] **Step 2: Run — expect FAIL**

```bash
cd web
npm run test -- src/bridge/callBridge.test.ts
```

- [ ] **Step 3: Implement errors + callBridge**

Create `web/src/bridge/bridgeErrors.ts`:

```typescript
export type BridgeErrorCode = "timeout" | "rejected" | "missing_method";

export class BridgeCallError extends Error {
  readonly code: BridgeErrorCode;
  readonly method: string;

  constructor(message: string, options: { code: BridgeErrorCode; method: string; cause?: unknown }) {
    super(message);
    this.name = "BridgeCallError";
    this.code = options.code;
    this.method = options.method;
    if (options.cause instanceof Error) {
      this.cause = options.cause;
    }
  }
}
```

Create `web/src/bridge/callBridge.ts`:

```typescript
import { BridgeCallError } from "./bridgeErrors";

export async function callBridge<T>(
  fn: () => Promise<T>,
  options: { method: string; timeoutMs?: number },
): Promise<T> {
  const timeoutMs = options.timeoutMs ?? 8_000;
  let timer: ReturnType<typeof setTimeout> | undefined;

  const timeoutPromise = new Promise<never>((_, reject) => {
    timer = setTimeout(
      () =>
        reject(
          new BridgeCallError(`Bridge call timed out: ${options.method}`, {
            code: "timeout",
            method: options.method,
          }),
        ),
      timeoutMs,
    );
  });

  try {
    return await Promise.race([fn(), timeoutPromise]);
  } catch (err) {
    if (err instanceof BridgeCallError) throw err;
    throw new BridgeCallError(`Bridge call failed: ${options.method}`, {
      code: "rejected",
      method: options.method,
      cause: err,
    });
  } finally {
    if (timer) clearTimeout(timer);
  }
}
```

- [ ] **Step 4: Run — expect PASS**

- [ ] **Step 5: Commit**

---

### Task 3: Bridge health helpers

**Files:**
- Create: `web/src/bridge/bridgeHealth.ts`

- [ ] **Step 1: Implement health types**

```typescript
export type BridgeKind = "mock" | "pywebview";

export type BridgeHealth = "ok" | "degraded" | "unavailable";

export function connectionLabel(
  kind: BridgeKind,
  health: BridgeHealth,
  detail?: string,
): string {
  if (kind === "mock") return detail ?? "Mock bridge (browser dev)";
  if (health === "ok") return detail ?? "Bridge connected";
  if (health === "degraded") return detail ?? "Bridge degraded — retrying";
  return detail ?? "Bridge unavailable";
}
```

- [ ] **Step 2: Commit**

---

### Task 4: Refactor `pywebviewBridge` (no silent mock fallback)

**Files:**
- Modify: `web/src/bridge/pywebviewBridge.ts`

- [ ] **Step 1: Replace implementation**

Key rules:
- If `window.pywebview.api` is **missing** → throw `BridgeCallError` with `code: "missing_method"` from factory (caller treats as unavailable).
- Each method uses `callBridge(() => call(api, snake_name, ...args), { method })`.
- **Remove** all `.catch(() => mockBridge.*)`.

```typescript
import type { NovelGuardBridge } from "./NovelGuardBridge";
import type { AppSnapshot } from "../types/snapshot";
import type { ReviewRowsPage, ReviewRowsQuery } from "../types/review";
import type { QualityIssueDetail, QualityRowsPage, QualityRowsQuery } from "../types/quality";
import type { SelectionScope } from "../types/selection";
import type { WorkMode } from "../types/snapshot";
import { BridgeCallError } from "./bridgeErrors";
import { callBridge } from "./callBridge";

type PyApi = Record<string, (...args: unknown[]) => Promise<unknown>>;

function getApi(): PyApi | null {
  if (typeof window === "undefined") return null;
  const w = window as unknown as { pywebview?: { api?: PyApi } };
  return w.pywebview?.api ?? null;
}

function call<T>(api: PyApi, method: string, ...args: unknown[]): Promise<T> {
  const fn = api[method];
  if (!fn) {
    return Promise.reject(
      new BridgeCallError(`pywebview api missing: ${method}`, {
        code: "missing_method",
        method,
      }),
    );
  }
  return fn(...args) as Promise<T>;
}

export function createPywebviewBridge(api: PyApi): NovelGuardBridge {
  return {
    getSnapshot: () => callBridge(() => call<AppSnapshot>(api, "get_snapshot"), { method: "get_snapshot" }),
    selectFolder: () =>
      callBridge(() => call(api, "select_folder").then(() => undefined), { method: "select_folder" }),
    startScan: (options) =>
      callBridge(() => call(api, "start_scan", options).then(() => undefined), { method: "start_scan" }),
    cancelRun: () =>
      callBridge(() => call(api, "cancel_run").then(() => undefined), { method: "cancel_run" }),
    setWorkMode: (mode: WorkMode) =>
      callBridge(() => call(api, "set_work_mode", mode).then(() => undefined), { method: "set_work_mode" }),
    queryReviewRows: (query: ReviewRowsQuery) =>
      callBridge(() => call<ReviewRowsPage>(api, "query_review_rows", query), {
        method: "query_review_rows",
      }),
    queryQualityRows: (query: QualityRowsQuery) =>
      callBridge(() => call<QualityRowsPage>(api, "query_quality_rows", query), {
        method: "query_quality_rows",
      }),
    getDuplicateGroupDetail: (groupId: string) =>
      callBridge(() => call<Record<string, unknown>>(api, "get_duplicate_group_detail", groupId), {
        method: "get_duplicate_group_detail",
      }),
    getQualityIssueDetail: (issueId: string) =>
      callBridge(() => call<QualityIssueDetail>(api, "get_quality_issue_detail", issueId), {
        method: "get_quality_issue_detail",
      }),
    getMovePreview: (selection: SelectionScope) =>
      callBridge(() => call<{ rows: unknown[] }>(api, "get_move_preview", selection), {
        method: "get_move_preview",
      }),
    applyResolvedActions: (selection: SelectionScope) =>
      callBridge(() => call(api, "apply_resolved_actions", selection).then(() => undefined), {
        method: "apply_resolved_actions",
      }),
  };
}

export function isPywebviewHost(): boolean {
  return getApi() !== null;
}

export function getPywebviewApi(): PyApi | null {
  return getApi();
}
```

- [ ] **Step 2: Update `bridgeParity.test.ts`**

Adjust fake API test to call `createPywebviewBridge(fakeApi)` instead of `createPywebviewBridge()` with window mock.

- [ ] **Step 3: Run contract + bridge tests**

```bash
cd web
npm run test:contracts
npm run test -- src/bridge/callBridge.test.ts
```

- [ ] **Step 4: Commit**

---

### Task 5: `SnapshotProvider` health + test bridge hook

**Files:**
- Modify: `web/src/app/providers/SnapshotProvider.tsx`
- Modify: `web/src/app/App.tsx` (pass connection health to header)
- Modify: `web/src/components/layout/AppHeader.tsx`

- [ ] **Step 1: Extend provider**

Add to `SnapshotProvider.tsx`:

```typescript
import { BridgeCallError } from "../../bridge/bridgeErrors";
import { connectionLabel, type BridgeHealth, type BridgeKind } from "../../bridge/bridgeHealth";
import { createPywebviewBridge, getPywebviewApi, isPywebviewHost } from "../../bridge/pywebviewBridge";

declare global {
  interface Window {
    __NOVELGUARD_TEST_BRIDGE__?: NovelGuardBridge;
  }
}

const HealthContext = createContext<BridgeHealth>("ok");
const BridgeKindContext = createContext<BridgeKind>("mock");

function resolveBridge(override?: NovelGuardBridge): { bridge: NovelGuardBridge; kind: BridgeKind } {
  if (override) return { bridge: override, kind: "mock" };
  if (typeof window !== "undefined" && window.__NOVELGUARD_TEST_BRIDGE__) {
    return { bridge: window.__NOVELGUARD_TEST_BRIDGE__, kind: "mock" };
  }
  const api = getPywebviewApi();
  if (api) return { bridge: createPywebviewBridge(api), kind: "pywebview" };
  return { bridge: mockBridge, kind: "mock" };
}
```

State: `health`, `connectionDetail`. On each `getSnapshot` tick:

```typescript
try {
  const next = await bridge.getSnapshot();
  if (alive) {
    setSnapshot(next);
    setHealth("ok");
    setConnectionDetail(undefined);
  }
} catch (err) {
  if (!alive) return;
  setHealth(err instanceof BridgeCallError && err.code === "timeout" ? "degraded" : "degraded");
  setConnectionDetail(err instanceof Error ? err.message : "Snapshot failed");
  // Keep last good snapshot if any; do not throw
}
```

Export `useBridgeHealth()` and `useBridgeKind()`.

Initial load: same try/catch; if no snapshot yet and failure, render banner:

```tsx
if (!snapshot && health !== "ok") {
  return (
    <div className="p-6 text-error" data-testid="bridge-unavailable">
      Bridge unavailable. {connectionDetail}
    </div>
  );
}
```

- [ ] **Step 2: Update AppHeader**

```typescript
export function AppHeader({
  route,
  connection,
  health = "ok",
}: {
  route: AppSnapshot["route"];
  connection: string;
  health?: "ok" | "degraded" | "unavailable";
}) {
  const tone =
    health === "ok"
      ? "border-success/30 bg-success/10 text-success"
      : health === "degraded"
        ? "border-secondary/30 bg-secondary/10 text-secondary"
        : "border-error/30 bg-error/10 text-error";
  // ... use tone on badge, data-testid="connection-badge"
}
```

In `AppContent`, compute:

```typescript
const kind = useBridgeKind();
const health = useBridgeHealth();
const connection = connectionLabel(kind, health, snapshot.connection);
```

- [ ] **Step 3: Manual check**

```bash
cd web && npm run dev
```

Browser: app loads with mock, header shows mock label.

- [ ] **Step 4: Commit**

---

### Task 6: Resolve grid query error + retry

**Files:**
- Modify: `web/src/features/work/ResolveAndOrganizeWorkspace.tsx`

- [ ] **Step 1: Add error state**

```typescript
const [queryError, setQueryError] = useState<string | null>(null);
```

In `loadPage` `try`:

```typescript
setQueryError(null);
const page = await bridge.queryReviewRows({ ... });
// existing setters
```

In `catch`:

```typescript
setQueryError(err instanceof Error ? err.message : "Failed to load rows");
if (!append) {
  setRows([]);
  setFilteredCount(0);
}
```

UI above grid (replace loading-only line):

```tsx
{queryError && (
  <div
    className="mx-4 mt-2 flex items-center justify-between rounded-md border border-error/40 bg-error/10 px-3 py-2 text-sm text-error"
    data-testid="resolve-query-error"
  >
    <span>{queryError}</span>
    <button
      type="button"
      data-testid="resolve-query-retry"
      className="rounded-md border border-outline px-2 py-1 text-xs font-semibold"
      onClick={() => void loadPage(null, false)}
    >
      Retry
    </button>
  </div>
)}
```

- [ ] **Step 2: Commit**

---

### Task 7: `ApplySubflowDialog` preview failure

**Files:**
- Modify: `web/src/features/work/ApplySubflowDialog.tsx`

- [ ] **Step 1: Add preview error state**

```typescript
const [previewError, setPreviewError] = useState<string | null>(null);
```

In `runPreview`:

```typescript
setPreviewError(null);
try {
  const result = await bridge.getMovePreview(selection);
  setPreviewCount(result.rows.length);
  setStep("confirm");
} catch (err) {
  setPreviewError(err instanceof Error ? err.message : "Preview failed");
  setStep("preview");
} finally {
  setBusy(false);
}
```

Render when `previewError`:

```tsx
<p className="mt-3 text-sm text-error" data-testid="apply-preview-error" role="alert">
  {previewError}
</p>
```

Confirm-step apply button: only render when `step === "confirm" && !previewError && previewCount > 0`.

Add `data-testid="apply-preview-run"` on preview button, `data-testid="apply-confirm-run"` on apply button.

- [ ] **Step 2: Commit**

---

### Task 8: `testBridge` + E2E helpers

**Files:**
- Create: `web/src/bridge/testBridge.ts`
- Create: `web/e2e/helpers/injectBridge.ts`

- [ ] **Step 1: testBridge factory**

```typescript
import type { NovelGuardBridge } from "./NovelGuardBridge";
import { mockBridge } from "./mockBridge";
import { BridgeCallError } from "./bridgeErrors";

type FailMode = "none" | "snapshot" | "queryReviewRows" | "getMovePreview";

export function createTestBridge(fail: FailMode): NovelGuardBridge {
  const base = mockBridge;
  const failCall = (method: string) => {
    throw new BridgeCallError(`E2E forced failure: ${method}`, { code: "rejected", method });
  };

  return {
    ...base,
    async getSnapshot() {
      if (fail === "snapshot") failCall("get_snapshot");
      return base.getSnapshot();
    },
    async queryReviewRows(query) {
      if (fail === "queryReviewRows") failCall("query_review_rows");
      return base.queryReviewRows(query);
    },
    async getMovePreview(selection) {
      if (fail === "getMovePreview") failCall("get_move_preview");
      return base.getMovePreview(selection);
    },
  };
}
```

- [ ] **Step 2: Playwright inject helper**

```typescript
import type { Page } from "@playwright/test";
import type { FailMode } from "../../src/bridge/testBridge";

export async function injectTestBridge(page: Page, fail: FailMode) {
  await page.addInitScript((mode) => {
    // Dynamic import not available in init script — inline minimal stub:
    (window as unknown as { __NOVELGUARD_TEST_BRIDGE_FAIL__?: string }).__NOVELGUARD_TEST_BRIDGE_FAIL__ =
      mode;
  }, fail);
}
```

Wire in `main.tsx` **before** `SnapshotProvider` mount (small dev-only block):

```typescript
// At top of App default export wrapper — read fail flag and set bridge via provider prop
```

Cleaner approach: in `resolveBridge`, if `window.__NOVELGUARD_TEST_BRIDGE_FAIL__` set, `return { bridge: createTestBridge(mode), kind: "mock" }`.

Add to `testBridge.ts` export and `SnapshotProvider` `resolveBridge` check for `__NOVELGUARD_TEST_BRIDGE_FAIL__`.

- [ ] **Step 3: Commit**

---

### Task 9: `data-testid` pass

**Files:**
- Modify: `web/src/features/work/WorkModeTabs.tsx`
- Modify: `web/src/features/work/resolve/BatchActionBar.tsx`
- Modify: `web/src/app/App.tsx` (sidebar Work nav if needed)

- [ ] **Step 1: Add stable selectors**

`WorkModeTabs` buttons:

```tsx
data-testid={`work-mode-tab-${tab.id}`}
```

`BatchActionBar` preview:

```tsx
data-testid="batch-preview-open"
```

`AppSidebar` Work button: `data-testid="nav-work"` (add to `AppSidebar.tsx`).

`Resolve` heading: `data-testid="resolve-workspace"` on main in `ResolveAndOrganizeWorkspace`.

- [ ] **Step 2: Commit**

---

### Task 10: Playwright smoke tests (5–7)

**Files:**
- Create: `web/e2e/smoke.spec.ts`

- [ ] **Step 1: Write spec**

```typescript
import { test, expect } from "@playwright/test";

test.describe("NovelGuard smoke", () => {
  test("app loads and shows snapshot strip", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByTestId("connection-badge")).toBeVisible();
    await expect(page.getByText(/Mock bridge|Bridge connected/i)).toBeVisible();
  });

  test("Work mode tabs switch scan resolve quality", async ({ page }) => {
    await page.goto("/");
    await page.getByTestId("nav-work").click();
    await page.getByTestId("work-mode-tab-scan").click();
    await expect(page.getByTestId("work-mode-tab-scan")).toHaveClass(/bg-primary/);
    await page.getByTestId("work-mode-tab-resolve").click();
    await expect(page.getByTestId("resolve-workspace")).toBeVisible();
    await page.getByTestId("work-mode-tab-quality").click();
    await expect(page.getByTestId("work-mode-tab-quality")).toHaveClass(/bg-primary/);
  });

  test("resolve grid loads rows from mock bridge", async ({ page }) => {
    await page.goto("/");
    await page.getByTestId("work-mode-tab-resolve").click();
    await expect(page.getByRole("grid")).toBeVisible({ timeout: 10_000 });
  });

  test("query failure shows error and retry", async ({ page }) => {
    await page.addInitScript(() => {
      (window as unknown as { __NOVELGUARD_TEST_BRIDGE_FAIL__?: string }).__NOVELGUARD_TEST_BRIDGE_FAIL__ =
        "queryReviewRows";
    });
    await page.goto("/");
    await page.getByTestId("work-mode-tab-resolve").click();
    await expect(page.getByTestId("resolve-query-error")).toBeVisible();
    await page.getByTestId("resolve-query-retry").click();
    await expect(page.getByTestId("resolve-query-error")).toBeVisible();
  });

  test("snapshot failure shows degraded connection", async ({ page }) => {
    await page.addInitScript(() => {
      (window as unknown as { __NOVELGUARD_TEST_BRIDGE_FAIL__?: string }).__NOVELGUARD_TEST_BRIDGE_FAIL__ =
        "snapshot";
    });
    await page.goto("/");
    await expect(page.getByTestId("bridge-unavailable")).toBeVisible();
  });

  test("preview failure blocks apply", async ({ page }) => {
    await page.goto("/");
    await page.getByTestId("work-mode-tab-resolve").click();
    await page.getByTestId("batch-preview-open").click();
    await page.evaluate(() => {
      (window as unknown as { __NOVELGUARD_TEST_BRIDGE_FAIL__?: string }).__NOVELGUARD_TEST_BRIDGE_FAIL__ =
        "getMovePreview";
    });
    await page.getByTestId("apply-preview-run").click();
    await expect(page.getByTestId("apply-preview-error")).toBeVisible();
    await expect(page.getByTestId("apply-confirm-run")).toHaveCount(0);
  });

  test("pywebview host without api shows unavailable", async ({ page }) => {
    await page.addInitScript(() => {
      (window as unknown as { pywebview?: { api?: unknown } }).pywebview = {};
    });
    await page.goto("/");
    await expect(page.getByTestId("bridge-unavailable")).toBeVisible();
  });
});
```

Adjust selectors after Task 5–9 land (grid role, nav-work). Fix preview test: set fail flag **before** navigation or inject at init with `getMovePreview` mode from start.

Simpler preview test:

```typescript
test("preview failure blocks apply", async ({ page }) => {
  await page.addInitScript(() => {
    (window as unknown as { __NOVELGUARD_TEST_BRIDGE_FAIL__?: string }).__NOVELGUARD_TEST_BRIDGE_FAIL__ =
      "getMovePreview";
  });
  await page.goto("/");
  await page.getByTestId("work-mode-tab-resolve").click();
  await page.getByTestId("batch-preview-open").click();
  await page.getByTestId("apply-preview-run").click();
  await expect(page.getByTestId("apply-preview-error")).toBeVisible();
  await expect(page.getByTestId("apply-confirm-run")).toHaveCount(0);
});
```

- [ ] **Step 2: Run E2E**

```bash
cd web
npm run test:e2e
```

Expected: 7/7 pass.

- [ ] **Step 3: Commit**

---

### Task 11: Docs + verification

**Files:**
- Modify: `docs/entry_points.md`

- [ ] **Step 1: Document E2E**

Append to `docs/entry_points.md`:

```markdown
## E2E smoke (PR-11)

```bash
cd web
npm run test:e2e
```

Requires Chromium (`npx playwright install chromium` once).
```

- [ ] **Step 2: Full verification**

```bash
cd web
npm run build
npm run test:contracts
npm run test:e2e
cd ..
python scripts/verify_phase_completion.py
```

- [ ] **Step 3: Commit**

```bash
git commit -m "[docs] PR-11 E2E smoke run path"
```

---

## Spec coverage self-review

| Spec / PR-11 requirement | Task |
|--------------------------|------|
| Work 3-mode tabs | Task 9 E2E |
| Resolve grid query-backed | Task 6 error path |
| Destructive preview→confirm→apply | Task 7 preview fail blocks apply |
| GlobalCommandBar only progress | No footer progress added |
| Bridge layering (no silent policy violation) | Task 4, 5 |
| No new screens | Only error banners |
| PR-10 contracts preserved | Task 11 regression |

**Gaps deferred:** PR-12 perf, PR-13 apply tokens, PR-14 packaging.

---

## Plan changelog

| Date | Note |
|------|------|
| 2026-06-01 | Initial PR-11 plan after PR-10 contract hardening |
| 2026-06-01 | Implemented: `dev:e2e` + 180s webServer timeout for reliable Playwright startup |

---

## Execution handoff

Plan complete and saved to `docs/superpowers/plans/2026-06-01-novelguard-ui-e2e-smoke.md`.

**Two execution options:**

1. **Subagent-Driven (recommended)** — fresh subagent per task, spec then quality review between tasks.

2. **Inline Execution** — run tasks in this session with checkpoints (review Task 4 bridge policy + Task 10 E2E closely).

Which approach?
