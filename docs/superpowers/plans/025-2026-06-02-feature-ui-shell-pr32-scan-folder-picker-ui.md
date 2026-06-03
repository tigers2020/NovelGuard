# PR-32: Scan Folder Picker UI — Implementation Plan

**Spec:** [019 scan folder picker UI](../specs/019-2026-06-02-feature-ui-shell-scan-folder-picker-ui-design.md) (**approved** 2026-06-03)

**Goal:** Restore user-visible folder selection on Work → Scan (LOCK-FOLDER-1..8).

**Scope:** `ScanWorkspace.tsx` only (+ tests if `TEST_ALLOWED`). No Python. Not PR-30.

**Plan status:** In progress

**Sequencing:** after PR #20 merge / after platform-polish PR-26..31 merge.

---

## Tasks

### Task 1: `ScanWorkspace` folder picker UI

**File:** `web/src/features/work/ScanWorkspace.tsx`

- [ ] Import `useBridge`, `useRefreshSnapshot` from `snapshotHooks`
- [ ] Import `BridgeCallError`; local `folderPickerErrorMessage(err)` (mirror `WorkRoute.workModeErrorMessage`)
- [ ] State: `isSelecting`, `folderError`
- [ ] Replace static **대상 폴더** block with:
  - truncated path: `library.folderPath ?? "폴더 미선택"`
  - button **폴더 선택** → `handleSelectFolder` (LOCK-FOLDER-2)
- [ ] Error strip when `folderError` set (`role="alert"`, `data-testid="scan-folder-error"` optional)
- [ ] Keep **스캔 시작** and scan options chips unchanged (LOCK-FOLDER-5, AC-5)

### Task 2: Wire-only check (no WorkRoute prop drilling)

- [ ] Confirm `ScanWorkspace` works inside PR-31 `WorkModePanel` without remount issues (local state OK)

### Task 3: Tests (gated)

**Requires user `TEST_ALLOWED` or equivalent.**

- [ ] Prefer extend existing `web/src/**/*.test.tsx` (e.g. new `ScanWorkspace.test.tsx` only if approved)
- [ ] Cases:
  - click **폴더 선택** → mock `selectFolder` spy
  - `refreshSnapshot` called after success
  - `LIBRARY_BUSY` → error strip text
- [ ] Optional e2e in `web/e2e/smoke.spec.ts`: path updates to mock `selected` segment

**Without TEST_ALLOWED:** manual smoke only; document in PR body.

### Task 4: Verification

- [ ] `cd web && npm run lint`
- [ ] `cd web && npm run test`
- [ ] `cd web && npm run test:e2e` (if Task 3 e2e added)
- [ ] Manual pywebview: dialog, cancel, select, scan

---

## Acceptance mapping

| Spec AC | Task |
|---------|------|
| AC-1..4 | 1, 4 manual |
| AC-5 | 1 |
| AC-6 | 1 (no Settings edits) |
| AC-7 | 1, 3 |
| AC-8 | 4 |

---

## Out of scope checklist

- [ ] No `BridgeApi` / `library_session.py` edits
- [ ] No `ShellFileDock` picker button
- [ ] No Settings route changes
- [ ] Not bundled into PR-30 bridge hygiene plan

---

## PR description snippet

```text
[pr32] Scan workspace folder picker CTA

- ScanWorkspace: 폴더 선택 → selectFolder + refreshSnapshot
- Restores scan entry UX; bridge unchanged
- Spec 019 / plan 025
```
