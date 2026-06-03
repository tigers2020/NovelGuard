---
title: Product Backlog (placeholder)
status: draft
date: 2026-06-03
parent_roadmap: docs/superpowers/roadmap/000-2026-06-01-novelguard-master-roadmap.md
---

# Product Backlog Roadmap

**Draft placeholder.** All release/automation tracks through **005** are closed on `main`.

When starting new work: rename this file (`006-YYYY-MM-DD-<area>-<topic>-roadmap.md`), set `status: active`, add spec → plan → implement per [agent-workflow.md](../agent-workflow.md).

## Candidate themes (not approved)

| Theme | Notes |
|-------|--------|
| Wave F polish | PR-26..29 items from [000 master](./000-2026-06-01-novelguard-master-roadmap.md) if still desired |
| i18n / expert settings | P2 in UI spec — deferred |
| Signed installer / auto-update | Out of beta scope — [known-limitations.md](../../release/known-limitations.md) |
| Hermes production | Point dispatcher at `hermes_job_stdin.py` + `run-worker-loop.ps1` on WSL |

## Gate before any PR

```bash
python scripts/verify_phase_completion.py
```
