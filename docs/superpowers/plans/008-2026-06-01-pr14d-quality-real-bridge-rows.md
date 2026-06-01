# PR-14d: QualityWorkspace Real Bridge Rows — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `QualityWorkspace` consumes `query_quality_rows` from the pywebview real bridge (14c backend), not mock-only row sources; bridge contract/parity is closed; backend failures surface explicit error state — never silent `mockBridge` fallback.

**Architecture:** Python `BridgeApi.query_quality_rows` already delegates to `LibrarySession` (14c). TS `createPywebviewBridge` maps `queryQualityRows` → `query_quality_rows` with `callBridge` (no mock fallback). `SnapshotProvider` picks `mockBridge` only when `window.pywebview.api` is absent (browser dev). PR-14d closes gaps: missing `app.bridge_parity`, client page validation on pywebview responses, mock `issueType` parity, Quality error/retry UX parity with Resolve, and contract/E2E guards.

**Tech Stack:** Python 3.12 (`BridgeApi`, pytest), React 19 + TypeScript (`web/`), Vitest, Playwright (extend existing `web/e2e/smoke.spec.ts` only).

**Spec:** [002-2026-06-01-novelguard-greenfield-library-session-design.md](../specs/002-2026-06-01-novelguard-greenfield-library-session-design.md) — `queryQualityRows` / `query_quality_rows` (14c data; 14d UI wire)

**Parent plans:** [007-2026-06-01-pr14c-quality-analyzer-and-rows.md](./007-2026-06-01-pr14c-quality-analyzer-and-rows.md) (**Done**)

**Test policy:** Extend existing modules only — `tests/test_bridge_contract.py`, `web/src/bridge/bridgeParity.test.ts`, `web/e2e/smoke.spec.ts`. No new `test_*.py` / `*.test.tsx` files unless user says `TEST_ALLOWED`.

**Non-goals (PR-14d):** QualityWorkspace layout/polish, issue detail drawer redesign, repair/UTF-8 execution, Finalize flow, near/relation quality, preview/apply real row ids (deferred), packaging/webview_main changes, `mockBridge` removal for browser dev.

---

## Plan-locked decisions

### Bridge selection (NOT fallback)

```text
OK:   browser dev, no pywebview → mockBridge (explicit dev mode)
OK:   pywebview.api ready → createPywebviewBridge(api)
NOT:  query_quality_rows throws → mockBridge.queryQualityRows()
NOT:  getSnapshot fails → switch bridge kind to mock
```

`SnapshotProvider.resolveBridge` already follows this; PR-14d adds tests/docs only — do not add catch-and-fallback in `pywebviewBridge` or `QualityWorkspace`.

### Row source of truth

| Host | Row source |
|------|------------|
| pywebview desktop | `LibrarySession._quality_rows_cache` via `BridgeApi.query_quality_rows` |
| Vite dev (no api) | `mockBridge.queryQualityRows` → `buildQualityRows()` |
| `QualityWorkspace` | **Only** `useBridge().queryQualityRows` — no `mockData` / `buildQualityRows` imports |

### Query contract (unchanged from 14c / PR-10)

```text
issueType: integrity | encoding | small_file (required)
issueType "near" or unknown → empty valid QualityRowsPage (rows: [])
limit: default 100, max 200 (clamp, not error)
cursor: offset string pagination (mockBridge + quality_query aligned)
```

### Error UX (minimal — error path only)

```text
queryQualityRows failure → queryError string, rows cleared on fresh load
data-testid="quality-query-error" (exists)
data-testid="quality-query-retry" (add — parity with resolve-query-retry)
data-testid="quality-workspace" on <main> (add — E2E anchor)
```

### Python parity module

```text
src/app/bridge_parity.py — canonical PYWEBVIEW_API_METHODS list
Must match web/src/contracts/bridgeParity.ts PYWEBVIEW_API_METHODS exactly (order + names)
tests/test_bridge_contract.py already imports this module (currently MISSING — blocks pytest)
```

---

## Current state (baseline)

| Item | Status |
|------|--------|
| `BridgeApi.query_quality_rows` | Present (`src/app/bridge_api.py`) |
| `LibrarySession.query_quality_rows` | Real cache (14c) |
| `pywebviewBridge.queryQualityRows` | Wired, no mock fallback |
| `QualityWorkspace` | Uses `bridge.queryQualityRows` — no direct `mockData` import |
| `web/src/contracts/bridgeParity.ts` | Lists `query_quality_rows` |
| `src/app/bridge_parity.py` | **Missing** — `pytest` collection fails on import |
| Quality retry button | Missing |
| E2E quality query failure | Missing |
| pywebview client `validateQualityRowsPage` | Missing (mockBridge validates) |

---

## File map

| File | Action |
|------|--------|
| `src/app/bridge_parity.py` | **Create** — `PYWEBVIEW_API_METHODS` canonical list |
| `src/app/bridge_api.py` | **Verify** — `query_quality_rows` unchanged unless parity drift |
| `web/src/contracts/bridgeParity.ts` | **Verify** — no drift vs Python list |
| `web/src/bridge/pywebviewBridge.ts` | **Modify** — validate `QualityRowsPage` after call |
| `web/src/bridge/mockBridge.ts` | **Modify** — unknown `issueType` → empty page (match Python) |
| `web/src/features/work/QualityWorkspace.tsx` | **Modify** — `data-testid`, retry only (no layout) |
| `tests/test_bridge_contract.py` | **Extend** — parity order test, re-run existing quality tests |
| `web/src/bridge/bridgeParity.test.ts` | **Extend** — import guard, anti-fallback doc test |
| `web/e2e/smoke.spec.ts` | **Extend** — quality query failure smoke |

---

## Acceptance criteria

```text
✓ pytest collects and passes (bridge_parity import fixed)
✓ BridgeApi exposes every PYWEBVIEW_API_METHODS name; query_quality_rows callable
✓ Python PYWEBVIEW_API_METHODS === TS PYWEBVIEW_API_METHODS (same length, same ordered names)
✓ issueType "near" → empty valid page (Python existing; mockBridge aligned)
✓ limit > 200 → capped at 200 (Python existing; mockBridge uses clampQualityQueryLimit)
✓ pywebviewBridge.queryQualityRows validates response; rejects malformed page
✓ pywebviewBridge does NOT import or call mockBridge
✓ QualityWorkspace: no mockData / buildQualityRows import; uses bridge only
✓ queryQualityRows failure → quality-query-error visible; quality-query-retry present
✓ E2E: __NOVELGUARD_TEST_BRIDGE_FAIL__=queryQualityRows shows quality-query-error
✓ npm run lint + python scripts/verify_phase_completion.py PASS
✓ mockBridge retained for browser dev; not used as runtime fallback on pywebview errors
```

---

### Task 1: Create `src/app/bridge_parity.py`

**Files:**
- Create: `src/app/bridge_parity.py`

- [ ] **Step 1: Add module** (must match `web/src/contracts/bridgeParity.ts` exactly)

```python
"""Canonical pywebview js_api method names (mirror web/src/contracts/bridgeParity.ts)."""

from __future__ import annotations

PYWEBVIEW_API_METHODS: tuple[str, ...] = (
    "get_snapshot",
    "select_folder",
    "start_scan",
    "cancel_run",
    "set_work_mode",
    "query_review_rows",
    "query_quality_rows",
    "get_duplicate_group_detail",
    "get_quality_issue_detail",
    "get_move_preview",
    "apply_resolved_actions",
    "discard_move_preview",
)
```

- [ ] **Step 2: Run test to verify import**

Run: `python -m pytest tests/test_bridge_contract.py::test_bridge_api_exposes_pywebview_methods -v`

Expected: PASS (was ERROR: ModuleNotFoundError `app.bridge_parity`)

- [ ] **Step 3: Commit**

```bash
git add src/app/bridge_parity.py
git commit -m "[bridge] add pywebview API parity list for contract tests"
```

---

### Task 2: Python ↔ TS parity test

**Files:**
- Modify: `tests/test_bridge_contract.py`

- [ ] **Step 1: Add test after imports** (locked list — not TS file parse; TS parity is `bridgeParity.test.ts`)

```python
def test_pywebview_api_methods_match_locked_contract() -> None:
    """Locked contract; must match web/src/contracts/bridgeParity.ts PYWEBVIEW_API_METHODS."""
    ts_methods = [
        "get_snapshot",
        "select_folder",
        "start_scan",
        "cancel_run",
        "set_work_mode",
        "query_review_rows",
        "query_quality_rows",
        "get_duplicate_group_detail",
        "get_quality_issue_detail",
        "get_move_preview",
        "apply_resolved_actions",
        "discard_move_preview",
    ]
    assert list(PYWEBVIEW_API_METHODS) == ts_methods
```

- [ ] **Step 2: Run**

Run: `python -m pytest tests/test_bridge_contract.py::test_pywebview_api_methods_match_locked_contract tests/test_bridge_contract.py::test_bridge_api_exposes_pywebview_methods -v`

Expected: PASS

- [ ] **Step 3: Re-run existing quality contract tests (14c regression)**

Run: `python -m pytest tests/test_bridge_contract.py -k "quality" -v`

Expected: PASS (`test_query_quality_rows_detects_issues`, `test_query_quality_rows_limit_capped_at_200`, `test_query_quality_rows_unknown_issue_type_empty`, etc.)

- [ ] **Step 4: Commit**

```bash
git add tests/test_bridge_contract.py
git commit -m "[tests] lock Python/TS pywebview method parity list"
```

---

### Task 3: Validate pywebview `queryQualityRows` response (client contract)

**Files:**
- Modify: `web/src/bridge/pywebviewBridge.ts`

- [ ] **Step 1: Import validator**

Add to imports:

```typescript
import { validateQualityRowsPage } from "../contracts/qualityPageContract";
```

- [ ] **Step 2: Wrap `queryQualityRows`**

Replace:

```typescript
    queryQualityRows: (query: QualityRowsQuery) =>
      callBridge(() => call<QualityRowsPage>(api, "query_quality_rows", query), {
        method: "query_quality_rows",
      }),
```

With:

```typescript
    queryQualityRows: (query: QualityRowsQuery) =>
      callBridge(async () => {
        const page = await call<QualityRowsPage>(api, "query_quality_rows", query);
        validateQualityRowsPage(page);
        return page;
      }, { method: "query_quality_rows" }),
```

- [ ] **Step 3: Run contract tests**

Run: `cd web && npm run test:contracts`

Expected: PASS (bridgeParity + callBridge + contracts)

- [ ] **Step 4: Commit**

```bash
git add web/src/bridge/pywebviewBridge.ts
git commit -m "[web] validate QualityRowsPage on pywebview queryQualityRows"
```

---

### Task 4: Align `mockBridge` unknown `issueType` with Python

**Files:**
- Modify: `web/src/bridge/mockBridge.ts`

- [ ] **Step 1: Early-return empty page for invalid issue types**

At start of `queryQualityRows`:

```typescript
  async queryQualityRows(query) {
    const valid: QualityIssueType[] = ["integrity", "encoding", "small_file"];
    if (!valid.includes(query.issueType)) {
      const empty = {
        rows: [],
        pageInfo: {
          cursor: query.cursor ?? null,
          nextCursor: null,
          hasMore: false,
          totalFiltered: 0,
        },
        summary: { issueCount: 0, warningCount: 0, errorCount: 0 },
      };
      validateQualityRowsPage(empty);
      return empty;
    }
```

(Add `QualityIssueType` to import from `../types/quality` if not already in scope.)

- [ ] **Step 2: Run contracts**

Run: `cd web && npm run test:contracts`

Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add web/src/bridge/mockBridge.ts
git commit -m "[web] mockBridge empty page for unknown quality issueType"
```

---

### Task 5: QualityWorkspace error path + E2E hooks (no layout polish)

**Files:**
- Modify: `web/src/features/work/QualityWorkspace.tsx`

- [ ] **Step 1: Add workspace test id on `<main>`**

```tsx
    <main
      className="flex h-full min-h-0 flex-col overflow-hidden bg-background p-5"
      data-testid="quality-workspace"
    >
```

- [ ] **Step 2: Replace the existing `queryError` block** (do not nest a second `{queryError && ...}` inside the old one)

Replace the entire existing block that renders `data-testid="quality-query-error"` with:

```tsx
        {queryError && (
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <p className="text-sm text-error" data-testid="quality-query-error">
              {queryError}
            </p>
            <button
              type="button"
              data-testid="quality-query-retry"
              className="rounded-md border border-outline px-3 py-1 text-sm font-semibold text-on-surface hover:bg-hover"
              onClick={() => void loadPage(null, false)}
            >
              Retry
            </button>
          </div>
        )}
```

- [ ] **Step 3: Manual smoke (browser dev)**

Run: `cd web && npm run dev`

1. Open Work → Quality tab.
2. Confirm grid loads rows (mock bridge).
3. DevTools: confirm no import from `mockData` in QualityWorkspace bundle (optional).

- [ ] **Step 4: Commit**

```bash
git add web/src/features/work/QualityWorkspace.tsx
git commit -m "[web] quality workspace query error retry and test ids"
```

---

### Task 6: Vitest guards (extend `bridgeParity.test.ts` only)

**Files:**
- Modify: `web/src/bridge/bridgeParity.test.ts`

- [ ] **Step 1: QualityWorkspace must not import mock row builders**

```typescript
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const repoRoot = join(dirname(fileURLToPath(import.meta.url)), "..", "..");

  it("QualityWorkspace does not import mockData or buildQualityRows", () => {
    const src = readFileSync(
      join(repoRoot, "src/features/work/QualityWorkspace.tsx"),
      "utf8",
    );
    expect(src).not.toMatch(/mockData/);
    expect(src).not.toMatch(/buildQualityRows/);
    expect(src).toMatch(/bridge\.queryQualityRows/);
  });
```

- [ ] **Step 2: pywebviewBridge must not reference mockBridge**

```typescript
  it("pywebviewBridge does not fall back to mockBridge", () => {
    const src = readFileSync(join(repoRoot, "src/bridge/pywebviewBridge.ts"), "utf8");
    expect(src).not.toMatch(/mockBridge/);
  });
```

- [ ] **Step 3: Run**

Run: `cd web && npm run test:contracts`

Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add web/src/bridge/bridgeParity.test.ts
git commit -m "[web] guard quality workspace and pywebview against mock fallback"
```

---

### Task 7: Playwright — quality query failure (extend existing smoke)

**Files:**
- Modify: `web/e2e/smoke.spec.ts`

- [ ] **Step 1: Add test**

```typescript
  test("quality query failure shows error and retry", async ({ page }) => {
    await page.addInitScript(() => {
      (window as unknown as { __NOVELGUARD_TEST_BRIDGE_FAIL__?: string }).__NOVELGUARD_TEST_BRIDGE_FAIL__ =
        "queryQualityRows";
    });
    await page.goto("/");
    await page.getByTestId("work-mode-tab-quality").click();
    await expect(page.getByTestId("quality-workspace")).toBeVisible();
    await expect(page.getByTestId("quality-query-error")).toBeVisible();
    await page.getByTestId("quality-query-retry").click();
    await expect(page.getByTestId("quality-query-error")).toBeVisible();
  });
```

- [ ] **Step 2: Run E2E**

Run: `cd web && npm run test:e2e`

Expected: PASS (all smoke tests including new one)

- [ ] **Step 3: Commit**

```bash
git add web/e2e/smoke.spec.ts
git commit -m "[e2e] quality query failure shows error without mock fallback"
```

---

### Task 8: Full verification

- [ ] **Step 1: Python gate**

Run: `python scripts/verify_phase_completion.py`

Expected: `pytest` PASS · `ruff` PASS · `mypy src` PASS · `black --check` PASS · `npm run lint` PASS

- [ ] **Step 2: Targeted regression checklist**

```bash
python -m pytest tests/test_bridge_contract.py -k "quality or bridge_api_exposes" -v
cd web && npm run test:contracts && npm run test:e2e
```

- [ ] **Step 3: Desktop manual (optional, recommended before push 14a–14d bundle)**

Run: `python src/main.py` (or project launcher)

1. Select folder with known empty/tiny/bad-UTF-8 files.
2. Run scan to completion.
3. Work → Quality → Integrity / Encoding / Small file tabs.
4. Confirm rows match scan issues (not mock paths like `D:/Novels/Library/raw/...`).
5. Snapshot stat chips align with row counts.

- [ ] **Step 4: Final commit if doc touch-ups**

Only if needed: `docs/superpowers/plans/008-...md` status table → mark tasks done when implementing.

---

## PR-14d test checklist (release gate)

| Check | Command / assertion |
|-------|-------------------|
| Lint | `npm run lint` (from repo root or `web/`) |
| Python tests | `pytest` |
| Full gate | `python scripts/verify_phase_completion.py` |
| `query_quality_rows` on BridgeApi | `test_bridge_api_exposes_pywebview_methods` |
| TS ↔ Python method parity | `test_pywebview_api_methods_match_locked_contract` + `bridgeParity.test.ts` |
| `issueType="near"` empty page | `test_query_quality_rows_unknown_issue_type_empty` |
| `limit > 200` capped | `test_query_quality_rows_limit_capped_at_200` |
| Backend unavailable (pywebview) | `pywebview host without api` E2E + `quality query failure` E2E |
| No mock row hardcode in workspace | `bridgeParity.test.ts` import guard |
| No silent mock fallback | `pywebviewBridge` source guard + PR-11 `callBridge` behavior |

---

## Plan self-review

| Requirement | Task |
|-------------|------|
| `BridgeApi.query_quality_rows` exposed | Baseline + Task 1–2 verify |
| `NOVEL_GUARD_BRIDGE_METHODS` ↔ `PYWEBVIEW_API_METHODS` | Task 1–2, 6 |
| TS `QualityRow` / `QualityRowsQuery` / `QualityRowsPage` | Baseline (`web/src/types/quality.ts`) — no change unless drift found |
| pywebview real backend call | Task 3 |
| mockBridge same contract, not fallback | Task 4, 6 |
| QualityWorkspace real query path | Task 5–7 |
| Explicit error state | Task 5, 7 |
| contract + unknown filter + limit 200 | Task 2, 4, 8 |
| No layout/polish/drawer/repair/finalize/near | Non-goals enforced |

**Placeholder scan:** No TBD steps. All code blocks are complete.

---

## Implementation status

| Item | Status |
|------|--------|
| PR-14d Tasks 1–8 | **Done** |

---

## Execution handoff

Plan complete and saved to `docs/superpowers/plans/008-2026-06-01-pr14d-quality-real-bridge-rows.md`.

**Two execution options:**

1. **Subagent-Driven (recommended)** — fresh subagent per task, review between tasks.
2. **Inline Execution** — run tasks in this session with `executing-plans`, batched checkpoints.

Which approach?
