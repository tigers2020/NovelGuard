# Superpowers Workflow

Use this area for deep context on non-trivial NovelGuard work.
Small/localized tasks should skip these docs and follow [AGENTS.md](../../AGENTS.md).

## Flow

1. Optional roadmap: `roadmap/NNN-YYYY-MM-DD-<area>-<topic>-roadmap.md`.
2. Spec: `specs/NNN-YYYY-MM-DD-<kind>-<layer>-<area>-<topic>-design.md`, then human approval.
3. Plan: `plans/NNN-YYYY-MM-DD-<kind>-<layer>-<area>-prNN-<topic>.md`, then human approval.
4. Implement with the smallest useful skill/process for the task.

## Naming

- `NNN` is directory-local.
- `prNN` is plan-only.
- New specs/plans need `risk: safe | destructive | breaking` frontmatter.
- Full rules: [agent-workflow.md](./agent-workflow.md#spec--plan-file-naming).
- Legacy pre-format files are grandfathered.

## Current Program Status

- Master roadmap: [000-2026-06-01-novelguard-master-roadmap.md](./roadmap/000-2026-06-01-novelguard-master-roadmap.md).
- Release gate roadmap: [003-2026-06-02-platform-release-gate-roadmap.md](./roadmap/003-2026-06-02-platform-release-gate-roadmap.md).
- Active IA spec (approved): [021-2026-06-02-feature-fullstack-shell-ia-reconciliation-design.md](./specs/021-2026-06-02-feature-fullstack-shell-ia-reconciliation-design.md).

### Track PR-33..36 (done in tree — 2026-06-03)

| PR | Plan | Deliverable |
|----|------|-------------|
| 33 | [027](./plans/027-2026-06-02-feature-fullstack-shell-pr33-ia-reconciliation.md) | Spec 021 approved, LOCK-33 |
| 34 | [028](./plans/028-2026-06-02-feature-ui-shell-pr34-work-mode-shell-cleanup.md) | 3-mode Work shell |
| 36 | [029](./plans/029-2026-06-02-feature-ui-resolve-pr36-duplicate-master-detail.md) | Resolve master-detail |
| 35 | [032](./plans/032-2026-06-02-feature-ui-scan-pr35-scan-section.md) | Unified scan section |
| 37 | [030](./plans/030-2026-06-02-feature-ui-work-pr37-finalize-subflow-dialog.md) | FinalizeSubflowDialog |

**MVP 3B (closed 2026-06-03):** PR-33..37 + [PR-42 bridge regression](./plans/031-2026-06-03-infra-bridge-quality-pr42-bridge-regression.md).

| 38 | [033](./plans/033-2026-06-02-feature-ui-shell-pr38-filedock-global.md) | FileDock global |
| 39 | [034](./plans/034-2026-06-02-feature-ui-shell-pr39-app-shell-polish.md) | App shell polish |
| 40 | [035](./plans/035-2026-06-02-feature-ui-settings-pr40-logs-settings-v2.md) | Logs/Settings v2 |

**Next:** [005 ops/automation roadmap](./roadmap/005-2026-06-03-ops-automation-roadmap.md). Tracks **003** / **004** closed 2026-06-03.

**Smoke scripts:** `launch_packaged_smoke.py`, `fixture_library_smoke.py` — [smoke-record-2026-06-03.md](../release/smoke-record-2026-06-03.md).

Historical specs and plans from before the full reset were removed with the codebase.
