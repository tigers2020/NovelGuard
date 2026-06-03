---
title: Bridge / App Hygiene Refactor
status: approved
risk: safe
grill_me: 2026-06-02
approved: 2026-06-02
date: 2026-06-02
pr_label: PR-30
parent_roadmap: docs/superpowers/roadmap/002-2026-06-02-pr26-pr30-platform-polish-roadmap.md
---

# 020 — Bridge / App Hygiene Refactor (PR-30)

## Status

**Approved** (2026-06-02) — grill G1–G10 locked below. **Contract cleanup only** — zero behavior drift vs PR-13..22 + PR-29.

---

## LOCK-30 — Scope freeze (verbatim)

```text
PR-30 does not add new bridge capabilities.
PR-30 does not change backend behavior.
PR-30 does not change UI behavior except error normalization where existing callers already handle the same semantic failure.
PR-30 is limited to bridge type hygiene, validator consistency, error shape normalization, dead adapter cleanup, and facade extraction behind identical BridgeApi methods.
Bridge behavior is unchanged. Type-only/interface parity repairs are allowed only where required by compilation or test parity.
```

### Grill locks (2026-06-02)

| # | Decision |
|---|----------|
| G1 | Feature PR? **No** — contract cleanup only |
| G2 | Python API shape change? **No** |
| G3 | mock/pywebview/testBridge parity? **Yes**, required |
| G4 | Validator merge? Allowed if behavior identical |
| G5 | Error code rename? **Forbidden** — alias/normalization only |
| G6 | Error union cleanup? Only when callers unaffected |
| G7 | Method delete? **Only** with unused proof (`query_review_rows_json`) |
| G8 | Snapshot invalidation redesign? **No** — PR-26 territory |
| G9 | New E2E files? **Forbidden** without `TEST_ALLOWED` |
| G10 | Contract responsibility table in plan? **Required** |

### Do not touch

| Lock | Paths |
|------|-------|
| PR-26 | `SnapshotProvider` poll/invalidation transport, invalidation event payload |
| PR-31 | `WorkRoute.tsx`, work-mode optimistic flow |
| PR-29 | `query_file_rows` ownership, SQL page path, `ShellFileDock` consumer |
| Parity | 27 `PYWEBVIEW_API_METHODS` names unchanged |

---

## Goals

1. Extract move preview/apply orchestration → `MovePreviewFacade`
2. Extract quality repair apply/discard orchestration → `QualityRepairFacade`
3. `BridgeApi` → thin delegate + validate-on-wire
4. Remove dead `query_review_rows_json`
5. Extend TS `parseBridgeRejection` for repair + finalize JSON/plain codes (no semantic change)
6. Characterization tests **before** facade merge

---

## Characterization matrix (extend `tests/test_bridge_contract.py`)

| Method | Case | Expected |
|--------|------|----------|
| `discard_quality_repair_preview` | mismatch token | idempotent; `hasPendingQualityRepair` false |
| `get_finalize_report` | unknown id | `FinalizeError("REPORT_NOT_FOUND")` |
| `set_app_setting` | unknown key | `PreviewApplyError("INVALID_SETTING_VALUE")` |
| `set_work_mode` | mode change | snapshot `work.activeMode` updates |

Existing coverage retained: move apply token flow, repair cross-block, finalize run/report.

---

## Facade boundaries

### MovePreviewFacade

- `_invalidate_pending_apply`, `_validate_apply`, `apply_resolved_actions`, `discard_move_preview`
- Depends: `LibrarySession`, `PreviewApplyGuard`, `ApplyResolvedActionsUseCase`

### QualityRepairFacade

- `_invalidate_pending_repair`, `_validate_repair_apply`, `apply_quality_repair`, `discard_quality_repair_preview`
- Depends: `LibrarySession`, `QualityRepairGuard`, `ApplyQualityRepairUseCase`

`get_move_preview` / `get_quality_repair_preview` stay on use cases via `BridgeApi` (already thin).

---

## Error wire shapes (documented — no change in PR-30)

| Exception | pywebview message |
|-----------|-------------------|
| `PreviewApplyError` | plain `reason` or message |
| `RepairApplyError` / `RepairPreviewError` | plain `reason` |
| `QualityQueryError` / `FileRowQueryError` / `ApplyFailedError` / `FinalizeError` | JSON `{"reason":…}` |

TS `toBridgeCallError` maps both JSON and bare allowlisted codes to `BridgeCallError.reason`.

---

## Acceptance

```bash
python scripts/verify_phase_completion.py
```

- All existing bridge contract tests pass
- New characterization cases pass
- Manual: preview→apply + repair preview→apply unchanged
- Plan documents `BridgeApi` responsibility map post-extract

---

## Plan

[026 PR-30 bridge hygiene](../plans/026-2026-06-02-refactor-bridge-pr30-bridge-hygiene.md)
