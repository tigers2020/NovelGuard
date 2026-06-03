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

**Next:** [030 PR-37 finalize subflow](./plans/030-2026-06-02-feature-ui-work-pr37-finalize-subflow-dialog.md) — after [pre-PR-37 gate](./roadmap/003-2026-06-02-platform-release-gate-roadmap.md#pre-pr-37-gate-track-cleanup--2026-06-03).

Historical specs and plans from before the full reset were removed with the codebase.
