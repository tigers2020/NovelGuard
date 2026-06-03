# PR-37: FinalizeSubflowDialog — Implementation Plan (draft)

**Spec:** [021 ia-reconciliation](../specs/021-2026-06-02-feature-fullstack-shell-ia-reconciliation-design.md) — **LOCK-33-7..12**, **LOCK-33-MVP-4**

**Depends on:** PR-33..36 merged or equivalent working tree ([pre-PR-37 gate](../roadmap/003-2026-06-02-platform-release-gate-roadmap.md#pre-pr-37-gate-track-cleanup--2026-06-03))

**Goal:** Replace the removed finalize **WorkMode tab** with `FinalizeSubflowDialog` (sheet/dialog) reusing `FinalizeWorkspace` capability route-free.

**Plan status:** Done (2026-06-03) — pre-PR-37 gate green; implemented in working tree

---

## Entry points (LOCK-33-10)

1. Resolve workspace — `최종 검증` CTA or blocker-aware banner
2. Quality workspace — `검증` / post-repair CTA
3. `ApplySubflowDialog` done panel — optional `최종 검증 계속`
4. `RepairSubflowDialog` done panel — optional `최종 검증 계속`

**Out of MVP (LOCK-33-11):** shell-level / sidebar finalize CTA

---

## Tasks (outline)

### Task 1: Extract shared finalize content

- [x] Refactor `FinalizeWorkspace.tsx` → route-free `FinalizeSubflowContent` (or similar)
- [x] Keep `data-testid` hooks used by future E2E

### Task 2: `FinalizeSubflowDialog` shell

- [x] App-level or Work-level dialog host (mirror `ApplySubflowDialog` pattern in `App.tsx`)
- [x] Steps: summary → blockers/warnings → cleanup opt-in → run → report
- [x] Progress via `GlobalCommandBar` only (Spec 000)

### Task 3: Wire entry CTAs

- [x] Resolve + Quality banners/buttons
- [x] Optional done-panel nudges on Apply/Repair subflows

### Task 4: Tests (extend existing)

- [x] `bridgeParity` / E2E smoke: open dialog from Resolve + Quality mock paths (no new test files)
- [x] `npm run lint` + `npm run test` + `npm run test:e2e`

### Task 5: Docs

- [x] Update plan status; roadmap 003 PR-37 → Done when merged

---

## Out of scope

- Full PR-41 cleanup debt
- New bridge finalize methods (use existing PR-23 surface)
- Shell-level finalize CTA (LOCK-33-11)

---

## Verification (planned)

```bash
cd web && npm run lint && npm run test
pytest tests/test_bridge_contract.py -k finalize -q
```
