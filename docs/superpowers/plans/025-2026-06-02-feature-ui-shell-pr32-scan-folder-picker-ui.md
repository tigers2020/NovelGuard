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

- [x] Import `useBridge`, `useRefreshSnapshot` from `snapshotHooks`
- [x] Import `BridgeCallError`; local `folderPickerErrorMessage(err)` (mirror `WorkRoute.workModeErrorMessage`)
- [x] State: `isSelecting`, `folderError`
- [x] Replace static **대상 폴더** block with:
  - truncated path: `library.folderPath ?? "폴더 미선택"`
  - button **폴더 선택** → `handleSelectFolder` (LOCK-FOLDER-2)
- [x] Error strip when `folderError` set (`role="alert"`, `data-testid="scan-folder-error"`)
- [x] Keep **스캔 시작** and scan options chips unchanged (LOCK-FOLDER-5, AC-5)

### Task 2: Wire-only check (no WorkRoute prop drilling)

- [x] Confirm `ScanWorkspace` works inside PR-31 `WorkModePanel` without remount issues (local state OK)

### Task 3: Tests (gated)

**Requires user `TEST_ALLOWED` or equivalent.**

- [ ] Prefer extend existing `web/src/**/*.test.tsx` (skipped — no TEST_ALLOWED)
- [ ] Manual smoke documented in PR body

### Task 4: Verification

- [x] `cd web && npm run lint` — 0 errors
- [x] `cd web && npm run test` — 73/73
- [ ] Manual pywebview: dialog, cancel, select, scan

**Plan status:** Complete (2026-06-03) pending manual pywebview smoke

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
