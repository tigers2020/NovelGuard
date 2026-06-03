---
title: Scan Section Reassembly (PR-35)
status: approved
risk: safe
approved: 2026-06-03
date: 2026-06-02
pr_label: PR-35
parent_roadmap: docs/superpowers/roadmap/003-2026-06-02-platform-release-gate-roadmap.md
parent_spec: docs/superpowers/specs/000-2026-06-01-novelguard-ui-overhaul-design.md
depends_on:
  - docs/superpowers/specs/021-2026-06-02-feature-fullstack-shell-ia-reconciliation-design.md
  - docs/superpowers/specs/019-2026-06-02-feature-ui-shell-scan-folder-picker-ui-design.md
---

# 023 — Scan Section Reassembly (PR-35)

## Status

**Approved** (2026-06-03). Plan [032](../plans/032-2026-06-02-feature-ui-scan-pr35-scan-section.md).

## Scope sentence

Consolidate Work → Scan into **one** `ScanWorkspace` section: folder picker, scan options chips, settings link, start/cancel, result summary, and `검토 · 정리로 이동` CTA. **Web-only**; no bridge/Python changes.

## LOCK-35

| ID | Rule |
|----|------|
| LOCK-35-1 | Single root `<section data-testid="scan-section">` with `data-state` per DESIGN.md |
| LOCK-35-2 | Folder picker from PR-32 preserved (`scan-select-folder`, error strip) |
| LOCK-35-3 | `library.scanOptions` chips + **스캔 설정** link → Settings route (no new settings keys) |
| LOCK-35-4 | Start scan + cancel when running (`scan-start`, `scan-cancel` → `cancelRun`) |
| LOCK-35-5 | Summary: file count, size, encoding issue count, last run |
| LOCK-35-6 | No duplicate scan CTA inside Scan besides this section (App pipeline stub unchanged) |
| LOCK-35-7 | Extend existing tests only (`web/e2e/smoke.spec.ts`) |

## `data-state` mapping

| `data-state` | Condition |
|--------------|-----------|
| `empty` | No `library.folderPath` |
| `running` | `work.scan.state === "running"` or `pipeline.phase === "scan"` |
| `error` | `work.scan.state === "error"` |
| `success` | `work.scan.state === "success"` |
| `ready` | Folder set; not running; not success/error |

## Out of scope

- Scan engine / bridge API changes
- ShellFileDock folder picker
- New settings fields

## Acceptance

- [x] Unified scan section visible on Work → 스캔 (2026-06-03)
- [x] `data-state` reflects folder + scan + pipeline
- [x] Settings link navigates to Settings route
- [x] `npm run lint` + `npm run test` + smoke scan tests pass
