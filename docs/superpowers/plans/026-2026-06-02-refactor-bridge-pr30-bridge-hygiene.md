# PR-30: Bridge Hygiene — Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans or subagent-driven-development.

**Spec:** [020 bridge hygiene](../specs/020-2026-06-02-refactor-bridge-bridge-hygiene-design.md) (**approved** 2026-06-02)

**Goal:** Thin `BridgeApi` via facades; dead code removal; TS error normalization — **behavior identical**.

**Plan status:** Complete (2026-06-02)

**Test policy:** Extend `tests/test_bridge_contract.py`, `web/src/bridge/callBridge.test.ts` only.

---

## BridgeApi responsibility map (post-PR-30)

| Region | Owner |
|--------|-------|
| Snapshot / scan / settings / logs / finalize | `BridgeApi` delegate |
| `query_*` + detail | `BridgeApi` + validators |
| Move apply / discard | `MovePreviewFacade` |
| Repair apply / discard | `QualityRepairFacade` |
| Preview use cases | `BridgeApi` → use case (unchanged) |

---

## Tasks

### Task 1: Characterization tests

- [x] `discard_quality_repair_preview` idempotent mismatch
- [x] `get_finalize_report` → `REPORT_NOT_FOUND`
- [x] `set_app_setting` unknown key → `INVALID_SETTING_VALUE`
- [x] `set_work_mode` updates snapshot mode
- [x] Parity test uses `PYWEBVIEW_API_METHODS` count (26)

### Task 2: MovePreviewFacade

- [x] `src/app/move_preview_facade.py`

### Task 3: QualityRepairFacade

- [x] `src/app/quality_repair_facade.py`

### Task 4: Wire BridgeApi + session_factory

- [x] Delegates; removed `query_review_rows_json`

### Task 5: TS error normalization

- [x] `parseBridgeRejection.ts` repair + finalize allowlists
- [x] `callBridge.test.ts` STALE_REPAIR_PREVIEW + REPORT_NOT_FOUND JSON
- [x] `INVALID_SETTING_VALUE` on `PreviewApplyErrorCode`

### Task 6: Verification

- [x] `python scripts/verify_phase_completion.py` — pytest 125/125, ruff, mypy, black, npm lint, packaging PASS
