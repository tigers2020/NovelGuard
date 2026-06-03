---
title: Bridge Regression Hardening (PR-42)
status: approved
risk: safe
approved: 2026-06-03
date: 2026-06-03
pr_label: PR-42
parent_roadmap: docs/superpowers/roadmap/003-2026-06-02-platform-release-gate-roadmap.md
depends_on:
  - docs/superpowers/specs/020-2026-06-02-refactor-bridge-bridge-hygiene-design.md
  - docs/superpowers/specs/001-2026-06-01-pr13-preview-token-stale-apply-design.md
  - docs/superpowers/specs/021-2026-06-02-feature-fullstack-shell-ia-reconciliation-design.md
---

# 022 — Bridge Regression Hardening (PR-42)

## Status

**Approved** (2026-06-03) — MVP stabilization slice (LOCK-33-MVP: PR-42 **or** PR-43). Plan [031](../plans/031-2026-06-03-infra-bridge-quality-pr42-bridge-regression.md).

## Scope sentence

Close **regression gaps** on the NovelGuard bridge: extend **existing** Python and Vitest contract/parity tests for post-PR-33..37 surfaces (3-mode `setWorkMode`, duplicate detail, finalize subflow RPCs, quality-repair stale/cross-block), and publish a **mock-only gaps** table. **No** new bridge methods, **no** behavior changes unless a test proves drift.

## In scope

| Area | Action |
|------|--------|
| Move preview / apply | Retain PR-13 matrix; ensure mock parity for `STALE_PREVIEW`, `SELECTION_CHANGED`, `NO_PENDING_APPLY` |
| Quality repair | mockBridge parity for `STALE_REPAIR_PREVIEW`, `REPAIR_PREVIEW_ACTIVE`, `MOVE_PREVIEW_ACTIVE` |
| IA (PR-34) | `set_work_mode` rejects `finalize`; mock + Python |
| PR-36/37 | `get_duplicate_group_detail`, finalize summary/run/report — parity already present; add gaps only if missing |
| `cancel_finalize` | Idempotent when idle (Python + mock) |
| Documentation | **LOCK-42-MOCK** — intentional mock-only behaviors |

## Out of scope

- New `*.test.ts` / `test_*.py` files (extend existing only)
- New bridge RPCs or error code renames
- PR-43 E2E full pipeline (separate PR)
- PR-41 finalize cleanup UX
- pywebview manual matrix (note only)

## LOCK-42 — Test policy

```text
Extend tests/test_bridge_contract.py and web/src/bridge/bridgeParity.test.ts only.
No new test files without TEST_ALLOWED.
No production behavior change unless fixing proven contract drift.
```

## Characterization matrix (PR-42 additions)

| Surface | Case | Expected |
|---------|------|----------|
| mockBridge | `applyQualityRepair` after `bumpLibraryRevisionForTest` | `STALE_REPAIR_PREVIEW`; pending cleared |
| mockBridge | `getMovePreview` while repair pending | `REPAIR_PREVIEW_ACTIVE` |
| mockBridge | `getQualityRepairPreview` while move pending | `MOVE_PREVIEW_ACTIVE` |
| mockBridge | `cancelFinalize` ×2 | no throw |
| Python | `cancel_finalize` when idle | no throw |
| Python + mock | `setWorkMode("finalize")` | `INVALID_WORK_MODE` (PR-34) |

Existing PR-13/22/30/36/37 tests are **retained**, not duplicated.

## LOCK-42-MOCK — Known mock-only gaps

| Gap | mockBridge | Python / pywebview |
|-----|------------|-------------------|
| Native folder picker | `selectFolder` sets deterministic path | tkinter `askdirectory` |
| Filesystem mutation on apply | Simulated / logged only for some paths | Real `LocalFilesystemApplyAdapter` on duplicate apply fixtures |
| Finalize cleanup dirs | Placeholder cleanup payload | Real pipeline per spec 011 |
| Scan progress | Timer-driven invalidation events | Session scan hooks |
| CP949 repair apply | Accepts token; does not rewrite bytes on disk | May rewrite file bytes in integration fixtures |
| `cancel_finalize` during run | Sets `pipelineRunning=false` | Sets cancel flag when `pipeline_phase==finalize` |

E2E and packaging smoke remain **PR-43 / PR-44**.

## Acceptance

- [x] Plan 031 tasks complete (2026-06-03)
- [x] `pytest tests/test_bridge_contract.py` PASS (117)
- [x] `cd web && npm run test -- src/bridge/bridgeParity.test.ts` PASS (44)
- [x] `python scripts/verify_phase_completion.py` PASS (2026-06-03)

## References

- Roadmap [003 PR-42](../roadmap/003-2026-06-02-platform-release-gate-roadmap.md#pr-42--bridge-regression-hardening)
- MVP lock [021 LOCK-33-MVP](../specs/021-2026-06-02-feature-fullstack-shell-ia-reconciliation-design.md)
