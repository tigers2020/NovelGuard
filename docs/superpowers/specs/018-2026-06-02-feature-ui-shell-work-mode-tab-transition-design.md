---
title: Work Mode Tab Transition — Optimistic Sync + CSS Keep-Alive
status: approved
risk: safe
grill_me: 2026-06-02
approved: 2026-06-02
date: 2026-06-02
authors: brainstorming + UI state review 2026-06-02
parent_spec: docs/superpowers/specs/000-2026-06-01-novelguard-ui-overhaul-design.md
related_specs:
  - docs/superpowers/specs/014-2026-06-02-snapshot-invalidation-design.md
  - docs/superpowers/specs/015-2026-06-02-quality-grid-parity-design.md
pr_label: PR-31
---

# 018 — Work Mode Tab Transition (Optimistic Sync + CSS Keep-Alive)

## Status

**Approved** (2026-06-02) — conditional approval from UI state / React layout review: A (optimistic sync) + B (full keep-alive) with **no HTML `hidden`**, `requestSeq` race guard, and explicit failure rollback (LOCK-18-1..4).

**Scope sentence:** Fix Work mode tab transitions (스캔 / 검토 · 정리 / 품질 / 적용 · 검증) so users no longer see **wrong-tab flash (D)** or **grid/layout jump (B)** when switching modes in **mock dev** and **pywebview**. Changes are **web-only** (`WorkRoute` and a small panel wrapper); **no** bridge/Python contract changes.

**Bridge boundary (review 2026-06-02):** Bridge behavior is unchanged. Type-only/interface parity repairs are allowed only where required by WorkRoute compilation or test parity (see plan 024).

---

## Locked decisions (brainstorming + review — 2026-06-02)

### LOCK-18 — verbatim

```text
LOCK-18-1  optimisticMode is NOT cleared in setWorkMode finally.
           Clear only in useEffect when snapshot.work.activeMode === optimisticMode.

LOCK-18-2  setWorkMode calls are guarded by requestSeq (monotonic) and lastRequestedMode.
           Stale request completion/failure must NOT overwrite a newer optimisticMode or UI error state.

LOCK-18-3  On setWorkMode failure for the latest request only: rollback optimisticMode to snapshotMode,
           show error toast/banner (reuse existing degraded/error patterns if present),
           and await refreshSnapshot() once.

LOCK-18-4  Work workspaces use CSS keep-alive panels: always mounted (**3 panels** after PR-34 per [Spec 021](./021-2026-06-02-feature-fullstack-shell-ia-reconciliation-design.md) LOCK-33-13; was 4 panels including finalize).
           Inactive panels use absolute inset-0 + invisible + pointer-events-none + aria-hidden;
           active panel uses visible + pointer-events-auto.
           Do NOT use HTML hidden attribute (display:none) for inactive panels.
           Use inert on inactive panels when supported (see §4.2).

LOCK-18-5  No bridge or Python changes. setWorkMode + getSnapshot contracts unchanged.

LOCK-18-6  No new test files without explicit user TEST_ALLOWED; extend existing e2e/unit where sufficient.
```

### Symptom → cause (as-is)

| Symptom | User report | Root cause (as-is) |
|---------|-------------|-------------------|
| **D** | Brief wrong tab content | `finally` clears `optimisticMode` before `snapshot.work.activeMode` updates (1s poll; no refresh after `setWorkMode`) → UI reverts to stale `snapshotMode` and remounts previous workspace |
| **B** | Grid height / column width jump | Conditional mount unmounts workspace + `VirtualizedDataGrid` remeasures from width 0; D causes double mount |

Confirmed in **mock dev** (`VITE_USE_MOCK_BRIDGE=true`) and **pywebview** — same UI path.

---

## 1. Problem

`WorkRoute` (`web/src/features/work/WorkRoute.tsx`) drives Work mode tabs:

- **Optimistic tab switch:** `optimisticMode ?? snapshot.work.activeMode`
- **Conditional render:** only the active workspace is mounted
- **Snapshot:** `SnapshotProvider` polls `getSnapshot()` every 1s; `setWorkMode` does not trigger refresh

Fast tab clicks and slow snapshot convergence produce visible glitches unacceptable for a data-heavy grid UI.

---

## 2. Goals

1. **No wrong-tab flash:** After clicking tab T, content for any other mode must not appear before T (success path).
2. **Reduced layout jump:** Returning to a mode preserves virtualized grid layout state (scroll, column widths) where possible.
3. **Race-safe rapid clicks:** Only the latest requested mode wins; stale bridge responses are ignored.
4. **Explicit failure UX:** Latest `setWorkMode` failure rolls back optimistic state and refreshes snapshot once.
5. **No backend churn:** Web-only; mock and pywebview both fixed by the same `WorkRoute` behavior.

---

## 3. Non-goals

- Changing snapshot poll interval (PR-26 / invalidation transport)
- ShellFileDock performance or `queryFileRows`
- Lazy keep-alive (mount on first visit only) — defer unless memory issues observed
- Memoizing snapshot slices for hidden workspaces (optional follow-up)
- New bridge methods or `activeMode` persistence changes on Python side

---

## 4. Design

### 4.1 Display mode and optimistic lifecycle (LOCK-18-1)

**State:**

- `snapshotMode` — `snapshot.work.activeMode`
- `optimisticMode: WorkMode | null`
- `displayMode = optimisticMode ?? snapshotMode` — used for tab highlight and panel visibility

**On tab click (`next`):**

1. Increment `requestSeq`; capture `const seq = requestSeq`.
2. `setOptimisticMode(next)`; record `lastRequestedMode = next`.
3. `await bridge.setWorkMode(next)`.
4. If `seq !== requestSeqRef.current`, **return** (stale) — no rollback, no error UI.
5. On success: `await refreshSnapshot()` (from `useRefreshSnapshot()`).
6. Do **not** clear optimistic in `try`/`finally`.

**Sync clear (useEffect):**

```ts
useEffect(() => {
  if (optimisticMode != null && snapshotMode === optimisticMode) {
    setOptimisticMode(null);
  }
}, [snapshotMode, optimisticMode]);
```

**Invariant (success path):** While `optimisticMode` is set and `snapshotMode !== optimisticMode`, UI stays on `optimisticMode` — never revert to stale `snapshotMode`.

### 4.2 Failure handling (LOCK-18-3)

When `setWorkMode` throws or rejects, and `seq` is still the latest:

1. `setOptimisticMode(null)` — display falls back to `snapshotMode` (rollback).
2. Show error — reuse existing connection/degraded banner or a small inline WorkRoute error strip if none exists (implementation choice: prefer existing `bridge` error patterns; no new toast library).
3. `await refreshSnapshot()` once.

Stale failures (`seq !== current`): no UI change.

### 4.3 Request sequencing (LOCK-18-2)

Use a ref for monotonic `requestSeq` incremented on each user-initiated mode change.

| Event | Action |
|-------|--------|
| User clicks mode M | `seq++`, optimistic M, start async work |
| Older request completes | Ignore if `seq` stale |
| Older request fails | Ignore if `seq` stale |
| Newer request in flight | Older results must not clear optimistic or show errors |

`lastRequestedMode` ref optional for debugging/tests; `requestSeq` is the authority.

### 4.4 CSS keep-alive panels (LOCK-18-4)

Replace conditional mount with **four always-mounted** workspace panels inside a single container:

```tsx
<div className="relative min-h-0 min-w-0 flex-1 overflow-hidden">
  <section
    aria-hidden={displayMode !== "scan"}
    inert={displayMode !== "scan" ? true : undefined}
    className={
      displayMode === "scan"
        ? "absolute inset-0 flex h-full min-h-0 flex-col overflow-hidden visible pointer-events-auto"
        : "absolute inset-0 flex h-full min-h-0 flex-col overflow-hidden invisible pointer-events-none"
    }
  >
    <ScanWorkspace … />
  </section>
  {/* resolve, quality, finalize — same pattern */}
</div>
```

**Rationale (review):** HTML `hidden` ⇒ `display: none` ⇒ virtualizer / `ResizeObserver` may see width 0 and defeat B. **`absolute inset-0` + `invisible`** keeps layout box size; inactive panels do not receive pointer events.

**`inert`:** Set on inactive sections when the React/runtime target supports it; omit attribute on active panel. If `inert` typing is awkward, use `inert=""` via spread only when inactive (match project TS DOM typings).

**ScanWorkspace props:** Still passed from snapshot when panel is inactive (re-renders on 1s poll are acceptable for v1).

### 4.5 `onGoResolve` and programmatic switches

`ScanWorkspace` “검토 · 정리로 이동” and any other `setModeOptimistic` call sites must use the **same** sequenced handler (single `requestWorkMode(next)` function) — no duplicate optimistic logic.

### 4.6 Files

| File | Change |
|------|--------|
| `web/src/features/work/WorkRoute.tsx` | Locks §4.1–4.5 |
| Optional `web/src/features/work/WorkModePanel.tsx` | Thin wrapper for §4.4 panel chrome (only if `WorkRoute` grows unwieldy) |

No changes to `WorkModeTabs.tsx` beyond using `displayMode` from parent (already the case).

---

## 5. Acceptance criteria (manual)

1. Mock dev + pywebview: rapidly switch **스캔 ↔ 검토 ↔ 품질 ↔ 적용** 10+ times — **no flash of a non-selected tab** (D).
2. In **검토**, scroll grid mid-list → **품질** → **검토**: scroll position and column widths **stable** (no full remount flash; minor 1s snapshot re-render acceptable) (B).
3. Tab highlight and visible panel **always match** `displayMode`.
4. Simulate `setWorkMode` failure (test bridge hook if available): latest failure shows error and UI matches `snapshotMode`; rapid click during failure does not leave orphan optimistic state.
5. Regression: existing e2e `Work mode tabs switch scan resolve quality` passes.

---

## 6. Testing strategy (LOCK-18-6)

| Layer | Action |
|-------|--------|
| E2E | Keep `web/e2e/smoke.spec.ts` work-mode tab test; optionally add rapid double-click tab (no new file) |
| Unit | Prefer testing `requestSeq` stale-ignore in a small pure helper if extracted — **only** in existing test file if one exists for WorkRoute; else manual + e2e |
| New files | Require `TEST_ALLOWED` |

---

## 7. Verification (implementation phase)

- `cd web && npm run lint`
- `cd web && npm run test` (or project `verify_phase_completion.py` when touching slice closure)
- Manual checklist §5 in mock dev and one pywebview run

---

## 8. Risks and follow-ups

| Risk | Mitigation |
|------|------------|
| Four mounted grids increase memory | Accept for v1 (four modes); lazy keep-alive if profiled |
| Hidden panels still re-render on 1s snapshot | Non-goal; follow-up: subscribe workspaces to `work` slice only |
| `inert` browser support | Progressive: `aria-hidden` + `pointer-events-none` required; `inert` best-effort |

---

## 9. Plan pointer

Implementation plan: [024 PR-31 work mode tab transition](../plans/024-2026-06-02-feature-ui-shell-pr31-work-mode-tab-transition.md) (**complete** 2026-06-02).

---

## Spec self-review (2026-06-02)

| Check | Result |
|-------|--------|
| Placeholders / TBD | None |
| Internal consistency | LOCK-18-1/3: success never rollback; failure rollback only latest — consistent |
| Scope | Single PR-sized web change |
| Ambiguity | Panel pattern fixed; no `hidden`; `cn()` not required |
| Contradictions | None with LOCK-29-4 (FileDock spec: no Work route changes **in PR-29**); this is a separate PR-31 Work UX fix |
