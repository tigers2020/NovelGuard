# PR-34: 3-Mode Shell Cleanup — Implementation Plan

**Spec:** [021 ia-reconciliation](../specs/021-2026-06-02-feature-fullstack-shell-ia-reconciliation-design.md) (**approved** 2026-06-03) — implements **LOCK-33-1, 2, 13**; amends **LOCK-18-4** (3 keep-alive panels)

**Goal:** Remove `finalize` as a WorkMode tab/route; narrow types and bridge validation to `scan | resolve | quality`.

**Scope:** `WorkModeTabs`, `WorkRoute`, `snapshot.ts`, `library_session.py`, `bridge_api.py`, `mockBridge.ts`, E2E smoke. **Keep** `FinalizeWorkspace.tsx` for PR-37 subflow extraction.

**Plan status:** Complete (2026-06-03)

---

## Tasks

### Task 1: TypeScript Work shell

**Files:** `web/src/types/snapshot.ts`, `WorkModeTabs.tsx`, `WorkRoute.tsx`

- [x] `WorkMode` = `scan | resolve | quality` only
- [x] Remove finalize tab and `WorkModePanel` for finalize
- [x] Tab labels per spec 021 wireframe

### Task 2: Bridge / session

**Files:** `src/application/library_session.py`, `src/app/bridge_api.py`, `web/src/bridge/mockBridge.ts`

- [x] `set_work_mode` accepts only 3 modes; reject `finalize`
- [x] Snapshot maps legacy `active_mode == finalize` → `resolve`

### Task 3: E2E

**File:** `web/e2e/smoke.spec.ts`

- [x] PR-31 rapid tab test cycles 3 modes only (no finalize workspace)

### Task 4: Contract test (extend existing)

**File:** `tests/test_bridge_contract.py`

- [x] `set_work_mode("finalize")` rejected; snapshot never returns finalize mode

### Task 5: Verification

- [x] `cd web && npm run lint` — 0 errors (1 pre-existing warning)
- [x] `cd web && npm run test` — 73/73
- [x] `pytest tests/test_bridge_contract.py::test_set_work_mode_updates_snapshot tests/test_bridge_contract.py::test_set_work_mode_rejects_finalize_mode -q` — 2/2

---

## Implementation status

**Done** (2026-06-03) — merged into pre-PR-37 track; see roadmap [pre-PR-37 gate](../roadmap/003-2026-06-02-platform-release-gate-roadmap.md#pre-pr-37-gate-track-cleanup--2026-06-03).

---

## Out of scope

- `FinalizeSubflowDialog` (PR-37)
- Scan section reassembly (PR-35 defer)
- Master-detail Resolve layout (PR-36)

---

## PR description snippet

```text
[pr34] 3-mode Work shell cleanup (LOCK-33-13)

- Remove finalize WorkMode tab/route; keep FinalizeWorkspace for PR-37
- Bridge rejects set_work_mode(finalize); migrate snapshot activeMode
- E2E PR-31 smoke updated for 3 panels
```
