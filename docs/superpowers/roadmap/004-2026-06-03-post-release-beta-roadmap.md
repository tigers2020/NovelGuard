---
title: Post-Release Beta & Operator Gate
status: active
date: 2026-06-03
parent_roadmap: docs/superpowers/roadmap/003-2026-06-02-platform-release-gate-roadmap.md
---

# Post-Release Beta Roadmap

**Position:** Track [003](./003-2026-06-02-platform-release-gate-roadmap.md) **closed** (PR-33..45). Engineering gate **7/7 PASS** on `main` 2026-06-03.

## Remaining (operator / optional build)

| Step | Owner | Artifact |
|------|-------|----------|
| Manual beta flows | Operator | [beta-readiness.md](../../release/beta-readiness.md) |
| Fresh Windows package | Operator | `python scripts/package_windows.py` + [packaging-smoke-checklist.md](../../release/packaging-smoke-checklist.md) |
| Push `main` | Engineering | `origin/main` includes plan 047 + automation governance |
| Hermes worker | Engineering | `automation/` + [agent-automation.md](../../agent-automation.md) |

## Done in tree

- Plan [047](../plans/047-2026-06-03-perf-large-library-near-relation.md) — large-library near/relation perf
- Automation-first `AGENTS.md` + `.cursor/rules/` + job runner

## Changelog

| Date | Change |
|------|--------|
| 2026-06-03 | Opened 004; 003 frozen; verify gate recorded |
