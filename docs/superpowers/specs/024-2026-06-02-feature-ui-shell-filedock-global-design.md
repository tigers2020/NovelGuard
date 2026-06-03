---
title: FileDock Global Alignment (PR-38)
status: approved
risk: safe
approved: 2026-06-03
date: 2026-06-02
pr_label: PR-38
parent_spec: docs/superpowers/specs/013-2026-06-02-shell-filedock-design.md
parent_roadmap: docs/superpowers/roadmap/003-2026-06-02-platform-release-gate-roadmap.md
---

# 024 — FileDock Global Alignment (PR-38)

## Scope sentence

Polish **shell-level** `ShellFileDock` per spec 000/013: `data-state`, Korean copy, Work hub cross-links (스캔 / 검토 · 정리), expand-on-request from Scan. **No** `queryFileRows` or bridge changes.

## LOCK-38

| ID | Rule |
|----|------|
| LOCK-38-1 | `data-testid="shell-file-dock"` + `data-state` = `empty` \| `collapsed` \| `expanded` |
| LOCK-38-2 | Cross-links: `shell-file-dock-open-resolve`, `shell-file-dock-open-scan` |
| LOCK-38-3 | Scan workspace: `scan-open-file-dock` expands dock (persisted) |
| LOCK-38-4 | Row activate → open Resolve (mode switch); no grid mutation |
| LOCK-38-5 | Persistence keys unchanged (`novelguard.shellFileDock.v1.*`) |

## Acceptance

- [x] Dock states + cross-links wired in App
- [x] Vitest + smoke dock paths green
