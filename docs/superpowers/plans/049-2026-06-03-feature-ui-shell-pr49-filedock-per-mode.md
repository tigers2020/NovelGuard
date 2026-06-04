# PR-49: ShellFileDock Per-Mode Persistence — Implementation Plan

> **For agentic workers:** Use subagent-driven-development or executing-plans.

**Goal:** Per-mode `expanded` localStorage so Scan dock preference survives Resolve/Quality visits.

**Architecture:** Extend `shellFileDockStorage.ts`; update `shellFileDockModePolicy.ts` + `App.tsx` + `ShellFileDock.tsx` toggle/persist paths.

**Spec:** [031](../specs/031-2026-06-03-feature-ui-shell-filedock-per-mode-design.md)

---

### Task 1: Storage + policy

**Files:**
- Modify: `web/src/components/layout/shellFileDockStorage.ts`
- Modify: `web/src/components/layout/shellFileDockModePolicy.ts`

- [ ] Add `loadFileDockExpandedForMode`, `persistFileDockExpandedForMode`, legacy migration
- [ ] Update policy: collapse/restore per mode; remove forced scan expand on mode entry

### Task 2: App + ShellFileDock wiring

**Files:**
- Modify: `web/src/app/App.tsx`
- Modify: `web/src/components/layout/ShellFileDock.tsx`

- [ ] Persist expanded using `snapshot.work.activeMode`
- [ ] Scan entry: `setFileDockExpanded(loadFileDockExpandedForMode("scan"))`

### Task 3: Tests

**Files:**
- Modify: `web/src/bridge/bridgeParity.test.ts`

- [ ] PR-49 vitest cases with `localStorage` clear in `beforeEach`

### Task 4: Verify

- [ ] `cd web && npm run lint`
- [ ] `cd web && npm run test -- src/bridge/bridgeParity.test.ts`

---

## Verification log

| Command | Status | Date |
|---------|--------|------|
| `npm run lint` | PASS | 2026-06-03 |
| `npm run test -- src/bridge/bridgeParity.test.ts` | PASS 57 | 2026-06-03 |

## Implementation status

**Done** (2026-06-03) on `feat/pr49-filedock-per-mode`.
