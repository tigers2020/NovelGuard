---
title: Ops and Automation Roadmap
status: closed
date: 2026-06-03
parent_roadmap: docs/superpowers/roadmap/000-2026-06-01-novelguard-master-roadmap.md
---

# Ops and Automation Roadmap

**Closed 2026-06-03.** Hermes queue, worker, beta smokes, CI alignment delivered on `main`.

## Delivered

| ID | Topic | Artifact |
|----|-------|----------|
| OPS-1 | Hermes dispatch | `hermes_enqueue.py`, `hermes_job_stdin.py`, `job-payload.schema.json` |
| OPS-2 | Worker | `automation_worker.py`, `run-worker.ps1`, `run-worker-loop.ps1` |
| OPS-3 | Beta gate | `beta_gate.py`, `fixture_library_smoke.py`, `launch_packaged_smoke.py` |
| OPS-4 | Large-library perf | Plan 047 perf — on `main` |
| OPS-5 | Resolve layout | Plan 047 layout — on `main` |

## Gates

```bash
python scripts/verify_phase_completion.py   # 9/9 when dist/ built
python scripts/beta_gate.py
python scripts/package_windows.py           # Windows package
```

## Changelog

| Date | Change |
|------|--------|
| 2026-06-03 | Opened 005 |
| 2026-06-03 | Closed — CI fixture smoke, Hermes stdin, worker loop, docs |
