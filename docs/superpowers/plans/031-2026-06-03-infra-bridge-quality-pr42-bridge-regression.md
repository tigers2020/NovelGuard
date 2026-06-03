# PR-42: Bridge Regression Hardening — Implementation Plan

**Spec:** [022 bridge regression](../specs/022-2026-06-03-infra-bridge-quality-bridge-regression-design.md) (**approved** 2026-06-03)

**Goal:** Close mock/Python parity gaps for stale apply, repair cross-block, and post-IA bridge surfaces; document mock-only gaps (LOCK-42-MOCK).

**Plan status:** Done (2026-06-03)

**Test policy:** Extend `tests/test_bridge_contract.py`, `web/src/bridge/bridgeParity.test.ts` only.

---

## Tasks

### Task 1: Spec + roadmap links

- [x] Spec 022 approved
- [x] Plan 031 created
- [x] Roadmap 003 phase index → PR-42 done

### Task 2: mockBridge quality-repair parity (Vitest)

- [x] `STALE_REPAIR_PREVIEW` after revision bump
- [x] `REPAIR_PREVIEW_ACTIVE` on move preview
- [x] `MOVE_PREVIEW_ACTIVE` on repair preview
- [x] `cancelFinalize` idempotent

### Task 3: Python characterization

- [x] `cancel_finalize` idempotent when idle

### Task 4: Verification gate

- [x] `pytest tests/test_bridge_contract.py -q` — 117 passed (2026-06-03)
- [x] `cd web && npm run test -- src/bridge/bridgeParity.test.ts` — 44/44 (2026-06-03)
- [x] `python scripts/verify_phase_completion.py` — see log below

### Task 5: mockBridge repair id resolution (parity fix)

- [x] `getQualityRepairPreview` matches normalized `quality:` ids to `buildQualityRows` ids
- [x] row-6 encoding fixture in `mockData.ts` for repair tests

---

## Verification log

| Command | Status | Date |
|---------|--------|------|
| `pytest tests/test_bridge_contract.py -q` | PASS 117 | 2026-06-03 |
| `npm run test -- src/bridge/bridgeParity.test.ts` | PASS 44 | 2026-06-03 |
| `python scripts/verify_phase_completion.py` | PASS | 2026-06-03 |
