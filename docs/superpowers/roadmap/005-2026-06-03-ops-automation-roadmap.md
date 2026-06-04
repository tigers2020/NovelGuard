---
title: Ops and Automation Roadmap
status: closed
date: 2026-06-03
parent_roadmap: docs/superpowers/roadmap/000-2026-06-01-novelguard-master-roadmap.md
---

# Ops and Automation Roadmap

**Closed 2026-06-03.** Hermes queue, worker, beta smokes, CI alignment delivered on `main`.

## Delivered

**Kanban:** [board](../../agent/KANBAN.md) — label `track-005` (OPS-1..OPS-5, column `done`).

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
