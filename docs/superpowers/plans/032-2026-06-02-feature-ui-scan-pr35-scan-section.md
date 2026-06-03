# PR-35: Scan Section Reassembly — Implementation Plan

**Spec:** [023 scan section](../specs/023-2026-06-02-feature-ui-scan-scan-section-design.md) (**approved** 2026-06-03)

**Goal:** One consolidated Scan section per LOCK-35.

**Plan status:** Done (2026-06-03)

**Test policy:** Extend `web/e2e/smoke.spec.ts`, `web/src/bridge/bridgeParity.test.ts` only.

---

## Tasks

### Task 1: `deriveScanSectionState` + unified `ScanWorkspace`

- [x] `web/src/features/work/scanSectionState.ts` — pure state mapper
- [x] Refactor `ScanWorkspace.tsx` — single `scan-section`, LOCK-35-1..5
- [x] `data-testid`s: `scan-section`, `scan-start`, `scan-cancel`, `scan-open-settings`, `scan-go-resolve`

### Task 2: Wire `WorkRoute` + `App`

- [x] `onCancelScan` → `bridge.cancelRun()`
- [x] `onOpenSettings` → `setRoute("settings")`

### Task 3: E2E + unit

- [x] `scan-section` `data-state` after folder pick
- [x] PR-35 settings link e2e
- [x] `deriveScanSectionState` tests in `bridgeParity.test.ts`

### Task 4: Verification

- [x] `cd web && npm run lint` — 0 errors
- [x] `cd web && npm run test` — 89/89
- [x] `cd web && npm run test:e2e -- --grep scan` — 3/3

---

## Verification log

| Command | Status | Date |
|---------|--------|------|
| `npm run lint` | PASS | 2026-06-03 |
| `npm run test` | PASS 89 | 2026-06-03 |
| `npm run test:e2e -- --grep scan` | PASS 3 | 2026-06-03 |
