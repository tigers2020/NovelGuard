---
title: ShellFileDock per-mode expanded persistence
status: approved
risk: safe
grill_me: 2026-06-03
approved: 2026-06-03
date: 2026-06-03
pr_label: PR-49
parent_spec: docs/superpowers/specs/029-2026-06-03-feature-ui-layout-pane-hierarchy-minimal-design.md
plan: docs/superpowers/plans/049-2026-06-03-feature-ui-shell-pr49-filedock-per-mode.md
roadmap: docs/superpowers/roadmap/007-2026-06-03-pr48-pr57-post-beta-roadmap.md
---

# 031 — ShellFileDock Per-Mode Expanded Persistence

## Scope sentence

Store **expanded** separately per Work mode (`scan`, `resolve`, `quality`) so Resolve/Quality auto-collapse no longer overwrites Scan dock preference. **Web-only** localStorage extension; height/density/columnPreset remain **global**. **LOCK-LAYOUT-2B** (hide expand on non-Scan) **deferred**.

---

## Problem

[029 LOCK-LAYOUT-2](029-2026-06-03-feature-ui-layout-pane-hierarchy-minimal-design.md) writes a single `novelguard.shellFileDock.v1.expanded=false` when entering Resolve/Quality. Returning to Scan leaves the dock collapsed even if the user had expanded it on Scan.

---

## Grill-me resolutions (self, 2026-06-03)

| Question | Decision |
|----------|----------|
| LOCK-LAYOUT-2B (disable expand on Resolve/Quality)? | **Deferred** — manual expand still allowed (Option A) |
| Keys | `expanded.scan`, `expanded.resolve`, `expanded.quality` |
| Legacy `expanded` | Migrate read → `expanded.scan` only; stop writing legacy key |
| On Resolve/Quality **entry** | UI **auto-collapse** (029 unchanged); write only that mode's key |
| On Scan **entry** | **Restore** `expanded.scan` (no forced expand when `fileCount > 0`) |
| `scan-open-file-dock` / reveal | Set `expanded.scan=true` + UI expanded |
| Bridge | No changes |

---

## LOCKs

| ID | LOCK |
|----|------|
| **LOCK-DOCK-49-1** | Per-mode keys under `novelguard.shellFileDock.v1.expanded.<mode>`. |
| **LOCK-DOCK-49-2** | Collapse policy for Resolve/Quality must not mutate `expanded.scan`. |
| **LOCK-DOCK-49-3** | Scan mode entry uses `loadFileDockExpandedForMode("scan")`, not forced true. |
| **LOCK-DOCK-49-4** | Layout keys (`heightPx`, `density`, `columnPreset`) stay global. |

---

## Acceptance

- [x] Spec approved 2026-06-03
- [x] Vitest: collapse resolve preserves scan=true
- [x] Vitest: `resolveInitialFileDockExpanded("scan")` restores scan pref
- [x] `npm run lint` + targeted vitest PASS
