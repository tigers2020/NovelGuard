# PR-31: Work Mode Tab Transition — Implementation Plan

**Spec:** [018 work mode tab transition](../specs/018-2026-06-02-feature-ui-shell-work-mode-tab-transition-design.md) (**approved** 2026-06-02)

**Goal:** Fix Work mode tab flash (D) and grid layout jump (B) via optimistic sync (LOCK-18-1..3) and CSS keep-alive panels (LOCK-18-4).

**Scope:** Web-only — `WorkRoute.tsx`, optional `WorkModePanel.tsx`. No bridge/Python changes.

**Bridge boundary (review 2026-06-02):**

```text
Bridge behavior is unchanged. Type-only/interface parity repairs are allowed only where required by WorkRoute compilation or test parity.
```

Included: `NovelGuardBridge.subscribeSnapshotInvalidation` interface + pywebview no-op stub; mockBridge `setAppSetting` error shape parity. No Python/transport semantic changes.

**Plan status:** Complete (2026-06-02)

---

## Tasks

### Task 1: Sequenced `requestWorkMode` handler

**File:** `web/src/features/work/WorkRoute.tsx`

- [x] `requestSeqRef` monotonic guard
- [x] Derived `pendingOptimistic` (replaces useEffect clear — same LOCK-18-1 invariant)
- [x] Success: `await refreshSnapshot()`; no rollback
- [x] Latest failure only: rollback, inline error strip, `refreshSnapshot()` once
- [x] Wire `WorkModeTabs`, `ScanWorkspace.onGoResolve` through single handler

### Task 2: CSS keep-alive panels

**Files:** `WorkRoute.tsx`, `WorkModePanel.tsx`

- [x] Four always-mounted panels in `relative` container
- [x] Inactive: `absolute inset-0 invisible pointer-events-none aria-hidden inert`
- [x] Active: `visible pointer-events-auto`
- [x] No HTML `hidden` attribute

### Task 3: Bridge type hygiene (pre-existing)

**Files:** `web/src/bridge/NovelGuardBridge.ts`, `pywebviewBridge.ts`, `mockBridge.ts`, `VirtualizedDataGrid.test.tsx`

- [x] Add `subscribeSnapshotInvalidation` to interface (mock already implements)
- [x] Fix mockBridge `setAppSetting` error shape parity

### Task 4: Verification

- [x] `cd web && npm run lint` — 0 errors
- [x] `cd web && npm run test` — 71/71
- [x] `cd web && npm run test:e2e` — 18/18

---

## Acceptance mapping

| Criterion | Task |
|-----------|------|
| No wrong-tab flash | 1, 2 |
| Grid scroll/column stable on return | 2 |
| Race-safe rapid clicks | 1 |
| Failure rollback + refresh | 1 |
| E2E regression | 4 |
