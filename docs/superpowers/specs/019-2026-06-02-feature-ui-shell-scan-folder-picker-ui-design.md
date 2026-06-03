---
title: Scan Folder Picker UI — Restore React Affordance
status: approved
risk: safe
approved: 2026-06-03
date: 2026-06-02
authors: PR triage / UX contract review 2026-06-02
parent_spec: docs/superpowers/specs/000-2026-06-01-novelguard-ui-overhaul-design.md
related_specs:
  - docs/superpowers/specs/002-2026-06-01-novelguard-greenfield-library-session-design.md
  - docs/superpowers/specs/018-2026-06-02-feature-ui-shell-work-mode-tab-transition-design.md
pr_label: PR-32
---

# 019 — Scan Folder Picker UI (Restore React Affordance)

## Status

**Approved** (2026-06-03) — gate review: restore ScanWorkspace folder picker CTA; web-only; LOCK-FOLDER-1..8.

**Scope sentence:** Add an explicit **폴더 선택** control on Work → Scan (`ScanWorkspace`) that calls `bridge.selectFolder()` then `refreshSnapshot()`. **Web-only**; no Python/bridge behavior changes.

**Sequencing:** after PR #20 merge / after platform-polish PR-26..31 merge → PR-32 Scan folder picker UI.

---

## Problem

| Layer | State |
|-------|--------|
| **Bridge** | `selectFolder()` / `select_folder()` implemented; desktop uses tkinter `askdirectory`; mock sets deterministic path |
| **React UI** | `ScanWorkspace` shows `library.folderPath` read-only; **no button** calls `selectFolder()` |
| **User impact** | “스캔 대상 선택” flow broken in pywebview and mock dev unless tests inject paths |

Legacy inventory (PySide / CompactBar era) placed folder selection outside the scan section; the React shell (`ShellFileDock`, `ScanWorkspace`) never re-hosted that CTA. Parent spec 000 lists folder path on **FileSummaryStrip** with global awareness — v1 shipped **ShellFileDock** path display only, not a picker.

---

## Locked decisions (LOCK-FOLDER — verbatim)

```text
LOCK-FOLDER-1
React UI must expose an explicit folder selection action in ScanWorkspace.

LOCK-FOLDER-2
The action calls bridge.selectFolder(), then immediately refreshSnapshot().

LOCK-FOLDER-3
No backend/Python behavior change. Existing LibrarySession.select_folder() remains the authority.

LOCK-FOLDER-4
Mock selectFolder() may keep using deterministic fake paths (no OS picker in browser dev).

LOCK-FOLDER-5
The selected folder path is displayed read-only after snapshot refresh.

LOCK-FOLDER-6
No new Settings fields for library path. Settings remain scan defaults only (extensions, hidden files).

LOCK-FOLDER-7
No new test files without explicit user TEST_ALLOWED; extend existing web unit/e2e only.

LOCK-FOLDER-8
Out of scope for PR-30 Bridge hygiene. Do not refactor BridgeApi or move picker to ShellFileDock in this PR unless product explicitly expands scope.
```

---

## Goals

1. User can choose scan library folder from **작업 → 스캔** without devtools or pytest injection.
2. After selection, snapshot shows updated `library.folderPath` and revision-driven dependents refresh via existing invalidation/poll.
3. Cancel picker → no error UI; previous path unchanged.
4. `LIBRARY_BUSY` (apply/scan in flight) surfaces inline error consistent with `WorkRoute` mode error strip pattern.

## Non-goals

- Backend folder picker implementation changes (tkinter remains).
- ShellFileDock “폴더 선택” duplicate CTA (optional follow-up).
- FileSummaryStrip resurrection as separate component.
- E2E OS native dialog automation (manual desktop smoke only).

---

## UI design

**Location:** `web/src/features/work/ScanWorkspace.tsx` — **대상 폴더** block.

**Layout:**

- Row: label + truncated path (read-only) + primary **폴더 선택** button.
- Use project tokens: `text-on-surface-variant`, `text-muted`, `border-outline`, existing button classes (match **스캔 시작** secondary/primary hierarchy — picker = secondary or outline, scan start stays primary).

**States:**

| State | UI |
|-------|-----|
| No folder | Path shows `폴더 미선택` (or `—` if snapshot null path; prefer explicit Korean copy per file dock) |
| Selecting | Button `disabled`, label e.g. `선택 중…` |
| Error | Inline strip below header row (`role="alert"`, reuse `WorkRoute` / `BridgeCallError` message pattern) |
| Success | Path updates from `useSnapshot()` after `refreshSnapshot()` |

**Handler (contract):**

```tsx
const handleSelectFolder = async () => {
  setIsSelecting(true);
  setFolderError(null);
  try {
    await bridge.selectFolder();
    await refreshSnapshot();
  } catch (err) {
    setFolderError(folderPickerErrorMessage(err)); // BridgeCallError + Error
  } finally {
    setIsSelecting(false);
  }
};
```

`ScanWorkspace` obtains `useBridge()` and `useRefreshSnapshot()` internally (same pattern as `FinalizeWorkspace` / `QualityWorkspace`).

**Accessibility:**

- Button: `type="button"`, visible label **폴더 선택**.
- Path region: `aria-live="polite"` optional when path changes after selection.

---

## Bridge contract (unchanged)

| Method | Desktop | Mock dev |
|--------|---------|----------|
| `selectFolder()` | Opens tkinter directory dialog; cancel = no-op | Sets `folderPath` to `D:/Novels/Library/selected`, bumps `libraryRevision`, emits invalidation |
| After call | `getSnapshot()` reflects new path | Same |

References:

- `src/application/library_session.py` — `select_folder`
- `src/app/bridge_api.py` — `select_folder`
- `web/src/bridge/NovelGuardBridge.ts` — `selectFolder`

---

## Acceptance criteria

| # | Criterion |
|---|-----------|
| AC-1 | **Desktop / pywebview:** Click **폴더 선택** → OS folder dialog (`스캔 폴더 선택`) |
| AC-2 | **Cancel dialog:** Previous `library.folderPath` unchanged; no error strip |
| AC-3 | **Confirm folder:** Path updates in Scan UI; `libraryRevision` increases (visible via resolve/file dock refresh) |
| AC-4 | **Mock dev:** Click updates to mock selected path without native dialog |
| AC-5 | **스캔 시작** remains available after folder selected (no regression) |
| AC-6 | **Settings:** No new library path field |
| AC-7 | **`LIBRARY_BUSY`:** Inline error when bridge rejects (mock: apply in progress) |
| AC-8 | `npm run lint` + `npm run test` pass; e2e extended if `TEST_ALLOWED` |

---

## Verification

**Automated (no new files without TEST_ALLOWED):**

- Extend `web` unit test that mounts `ScanWorkspace` with test bridge stub: click → `selectFolder` called → refresh invoked.
- Optional e2e: mock dev click **폴더 선택** → path text contains `selected`.

**Manual:**

- pywebview: pick real folder, start scan, confirm file dock count updates.

---

## Dependencies

| PR | Relationship |
|----|----------------|
| PR-31 | Done — keep-alive Scan panel stays mounted; picker state local to `ScanWorkspace` |
| PR-30 | **Must not include** this work |
| PR-32 | Implements this spec |

---

## References

- [002 Library session](../specs/002-2026-06-01-novelguard-greenfield-library-session-design.md) — `select_folder` lifecycle
- [000 UI overhaul](../specs/000-2026-06-01-novelguard-ui-overhaul-design.md) — `selectFolder()` in bridge table
- [entry_points.md](../../entry_points.md) — desktop vs mock bridge
- Roadmap: [002 PR-26..30](../roadmap/002-2026-06-02-pr26-pr30-platform-polish-roadmap.md) — PR-32 row (this track)
