# PR-16: Resolve UI Apply Outcome — Implementation Plan

**Spec:** [004-2026-06-01-resolve-ui-apply-outcome-design.md](../specs/004-2026-06-01-resolve-ui-apply-outcome-design.md)

**Status:** Implemented 2026-06-01

## Tasks

- [x] `parseBridgeRejection` + `ApplyFailedError` JSON `__str__`
- [x] `ApplySubflowDialog` summary, table, done step, partial-failure copy
- [x] `useRefreshSnapshot` after apply
- [x] `mockBridge` bumps `libraryRevision` on successful apply
- [x] Extend `callBridge.test.ts` for rejection parsing

## Verification

```bash
cd web && npm run test:contracts
cd web && npm run test:e2e
python -m pytest tests/test_bridge_contract.py -q
```
