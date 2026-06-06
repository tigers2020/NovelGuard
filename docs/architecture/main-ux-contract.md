---
title: Main UX contract (stabilization baseline)
status: locked
date: 2026-06-06
supersedes_confusion:
  - work-hub single vertical scroll (not implemented; deferred)
  - 4th WorkMode tab for Finalize (removed per spec 021)
related_specs:
  - docs/superpowers/specs/000-2026-06-01-novelguard-ui-overhaul-design.md
  - docs/superpowers/specs/021-2026-06-02-feature-fullstack-shell-ia-reconciliation-design.md
  - docs/superpowers/specs/013-2026-06-02-shell-filedock-design.md
---

# Main UX contract

> **Authority:** `main` branch code + tests at time of stabilization PR.
> **Agents:** Do not implement alternate IA (work-hub single scroll, 4-mode tabs) until this contract is explicitly revised.

## Current IA (locked)

| Surface | Contract |
|---------|----------|
| Work route | **3 WorkMode tabs:** `scan` · `resolve` · `quality` (`WorkRoute`, `WorkModeTabs`) |
| Mode panels | Keep-alive workspaces: `ScanWorkspace`, `ResolveAndOrganizeWorkspace`, `QualityWorkspace` |
| Subflows | **Dialog overlays only:** `ApplySubflowDialog`, `FinalizeSubflowDialog`, `PreflightPipelineDialog`, repair subflows — **not** top-level tabs |
| Shell | `AppShell` + global `ShellFileDock` (per-mode collapse policy); no duplicate dock inside Work |
| Settings / Logs | Separate routes from Work |

This is the **Hybrid 3-mode** IA from spec 000, reconciled by spec 021. It is **not** a single-scroll work-hub.

## Deferred / not on main

| Topic | Status | Notes |
|-------|--------|-------|
| work-hub single vertical scroll | **Deferred** (LOCK-33-13) | Do not treat roadmap prose as implemented |
| Finalize as 4th WorkMode tab | **Superseded** by spec 021 | Finalize capability via `FinalizeSubflowDialog` |
| Bulk auto-approve server job | **Done** — PR #66 / #67 | `startResolveAutoApproveJob` + UI polling |
| Finalize async bridge job | **Done** — PR #68 | `startFinalizeJob` / `getFinalizeJob` / `cancelFinalize`; non-blocking bridge |
| Apply preview display rows | **Done** — PR #60 (`d66f40ed`) | Spec/plan approved PR #61 |

## Application boundary (preserve)

Post-scan and apply pipelines live in `LibrarySession` + use cases (`src/application/`, `src/app/`). UI refactors must **not** duplicate scan/duplicate/near/relation/apply orchestration inside React.

Background phases (relation, near, projection) may bump `library_revision`; move preview pending state is guarded by `PreviewApplyGuard` / `hasPendingApply`.

## Spec numbering note

Roadmap 007 reserves `035` / `036` filenames for **PR-53 settings** and **PR-54 packaged E2E**. The 2026-06-05 work specs reuse those numbers for different topics. Until renumbered, disambiguate by **full filename** or date prefix, not NNN alone.

## Verification

Stabilization PR is docs-only. No behavior change required. Feature PRs must run scoped tests per AGENTS.md.
