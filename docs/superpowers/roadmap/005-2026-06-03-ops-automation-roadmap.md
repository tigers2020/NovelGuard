---
title: Ops and Automation Roadmap
status: active
date: 2026-06-03
parent_roadmap: docs/superpowers/roadmap/000-2026-06-01-novelguard-master-roadmap.md
---

# Ops and Automation Roadmap

**Position:** Release tracks **001**, **003**, **004** closed. `verify_phase_completion.py` runs **9/9** including beta smokes.

## Active workstreams

| ID | Topic | Entry | Status |
|----|-------|-------|--------|
| OPS-1 | Hermes job dispatch | `hermes_enqueue.py`, `hermes_job_stdin.py` (stdin JSON) | **Done** |
| OPS-2 | Local worker | `automation_worker.py`, `run-worker-loop.ps1` | **Done** |
| OPS-3 | One-shot beta gate | `beta_gate.py` | **Done** |
| OPS-4 | Large-library perf | Plan [047 perf](../plans/047-2026-06-03-perf-large-library-near-relation.md) | Done on `main` |
| OPS-5 | Resolve layout polish | Plan [047 layout](../plans/047-2026-06-03-feature-ui-layout-pane-hierarchy-minimal.md) | Done on `main` |

## Gates

```bash
python scripts/verify_phase_completion.py   # 9/9 when dist/ built
python scripts/beta_gate.py                 # smokes only
python scripts/package_windows.py         # optional full build
```

## Changelog

| Date | Change |
|------|--------|
| 2026-06-03 | Opened 005 after 004 close |
