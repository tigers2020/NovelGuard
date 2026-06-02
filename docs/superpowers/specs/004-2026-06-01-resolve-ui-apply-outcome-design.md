---
title: PR-16 Resolve UI Apply Outcome
status: approved
date: 2026-06-01
parent_spec: docs/superpowers/specs/003-2026-06-01-real-apply-use-cases-design.md
plan: docs/superpowers/plans/010-2026-06-01-pr16-resolve-ui-apply-outcome.md
---

# PR-16: Resolve UI Real Apply Outcome

## Goal

Surface PR-15 real apply behavior in the **Apply subflow** UI: preview summary, executable row table, success panel, and structured `APPLY_FAILED` / stale messaging — without new bridge methods or FS mutations.

## In scope

| Area | Behavior |
|------|----------|
| Preview step | Show `summary` chips (`operationCount`, `rowCount`, `conflictCount`, `blockedCount`) + `rows` table |
| Confirm | Disable apply when `operationCount === 0` |
| Apply success | `done` step + `apply-success-panel`; immediate snapshot refresh |
| Apply partial | `APPLY_FAILED` + `details` (succeededCount, failedRowId, refreshError) |
| Stale | Existing stale banner; PR-13 guards unchanged |
| pywebview errors | Parse `PreviewApplyError` string or `ApplyFailedError` JSON `__str__` |

## Out of scope

- New `ApplyResult` bridge method (void apply remains)
- Per-row post-apply grid status (PR-17)
- Audit log viewer UI
- Delete / trash

## Boundary (from spec 003)

PR-15 owns FS + audit write; PR-16 owns user-facing copy and preview/result panels only.

## Approval

- [x] 2026-06-01 — Thin follow-on to approved spec 003 § PR-16 boundary
