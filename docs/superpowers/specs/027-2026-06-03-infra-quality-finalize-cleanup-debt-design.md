---
title: Finalize Pipeline Debt (PR-41)
status: approved
risk: safe
approved: 2026-06-03
pr_label: PR-41
parent_spec: docs/superpowers/specs/011-2026-06-02-finalize-cleanup-pipeline-design.md
---

# 027 — Finalize Pipeline Debt (PR-41)

## Scope

- Bridge `previewFinalizeCleanup` — list empty dirs before run (read-only)
- UI: cleanup preview panel, post-run removed list, `data-state`, logs link
- mock parity + contract tests (extend existing files)

## LOCK-41

- No new test files
- Runner thread model unchanged (PR-23)
- Cleanup allowlist unchanged (G5)
