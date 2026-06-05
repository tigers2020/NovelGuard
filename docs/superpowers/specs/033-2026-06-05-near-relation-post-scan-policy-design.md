---
title: NOV-26 Near/Relation Post-Scan Handling Policy
status: approved
date: 2026-06-05
linear: NOV-26
parent: NOV-25
related_specs:
  - docs/superpowers/specs/007-2026-06-01-near-duplicate-detection-design.md
  - docs/superpowers/specs/008-2026-06-02-relation-filename-blocking-design.md
  - docs/superpowers/specs/011-2026-06-02-finalize-cleanup-pipeline-design.md
branch: ai/NOV-26-near-relation-post-scan-policy
---

# NOV-26 — Near/Relation Post-Scan Handling Policy

## Summary (caveman)

- **Decision:** Hybrid **A+D** — near/relation stay `unreviewed`; primary queue metric = exact unresolved file rows only.
- **Reject B/C** for v1 — no post-scan auto-approve/exclude mutator.
- **Implementation:** NOV-27 adds `moveReadyCount` + `reviewSignalCount`; keep aggregate `queueCount`.
- **Finalize:** `exactUnresolvedQueueCount` already exact-only (G2); ADR documents alignment.
- **Deliverable:** this file only — no product code in NOV-26.

## Problem statement

After scan, near/relation file members are materialized with `status: "unreviewed"` and `proposedAction` ∈ `{keep, ignore}` (never `move_duplicate`). Apply is hard-blocked. Yet `snapshot.work.resolve.queueCount` counts **all** unresolved file rows (exact + near + relation), inflating the primary "Queue" chip. Users interpret this as "work left to move" when near/relation are **review-only signals**.

Exact non-keepers are auto-approved post-scan (NOV-17). Near/relation receive **no** analogous post-scan mutation today.

## Decision (Hybrid A + D)

| Layer | Policy |
|-------|--------|
| **Persistence (A)** | Near/relation file rows **remain** `unreviewed` after post-scan unless user explicitly changes status. No post-scan auto-approve or auto-exclude in v1. |
| **Presentation (D)** | Primary Resolve queue indicator uses **`moveReadyCount`** — exact file rows only with `status ∈ {unreviewed, conflict}`. |
| **Diagnostic** | Retain aggregate `queueCount` (all types) in snapshot/DTO. |
| **Signals** | Near/relation counts exposed as `reviewSignalCount` for transparency. |

### Rejected for v1

| Option | Rationale |
|--------|-----------|
| **B** Auto-mark reviewed | Mutates SQLite without user intent; hides signals from default filters. |
| **C** Auto-exclude | Same as B; alters `excluded` semantics. |
| **Pure A** (no D) | Leaves misleading primary queue UX. |

## Count semantics (normative)

| Semantic | Definition | Snapshot field (NOV-27) | Finalize field |
|----------|------------|-------------------------|----------------|
| Move-ready queue | `rowKind=file`, `type=exact`, `status ∈ {unreviewed, conflict}` | `moveReadyCount` | `exactUnresolvedQueueCount` |
| Review-only signals | `rowKind=file`, `type ∈ {near, relation}`, same statuses | `reviewSignalCount` | (warnings G3 only) |
| Aggregate diagnostic | All file rows unresolved | `queueCount` | `queueCount` |

**Invariant:** `queueCount === moveReadyCount + reviewSignalCount` when row types partition unresolved file rows.

**Rules:**

1. Count file rows only (`rowKind === "file"`).
2. Finalize blocker MUST use exact-only count (G2) — not raw `queueCount`.
3. Post-scan worker MUST NOT add near/relation auto-approve/exclude hooks in v1.

## Rationale vs PR-19 / PR-20 / Finalize

| Constraint | How hybrid A+D satisfies |
|------------|---------------------------|
| PR-19 near review-only apply | No apply path opened; rows stay visible when user filters `types: ["near"]`. |
| PR-20 relation review-only apply | Same for `types: ["relation"]`. |
| Finalize G2 `exactUnresolvedQueueCount` | Blocker already exact-only; primary chip aligns user-facing "queue" with finalize blocker source. |
| Finalize G3 warnings | Unreviewed near/relation still drive **warnings**, not blockers — unchanged. |
| NOV-17 exact auto-approve | Exact-only post-scan mutator remains sole automatic status writer. |

## UI copy rules

| Surface | Binding |
|---------|---------|
| Resolve toolbar primary chip | `moveReadyCount` — label `이동 대기` (NOV-27) |
| Signal chip | `reviewSignalCount` — label `참고 신호` (NOV-27) |
| Preflight pipeline dialog | Lead with `moveReadyCount`; footnote `reviewSignalCount` if > 0 (follow-up) |
| Grid row badges | Unchanged — near/relation visible when type filter includes them |

## Implementation boundaries

| In NOV-26 (this issue) | Follow-up (NOV-27) |
|------------------------|---------------------|
| ADR file merged | `review_snapshot_counts.py` + `dto_mapper.py` emit lane counts |
| Link from NOV-25 epic | `ResolveGridToolbar.tsx` chip relabel |
| Post-scan mutator lock documented | `bridge_contract.py` + contract tests |

## Follow-up issues

| ID | Scope |
|----|-------|
| NOV-27 | Snapshot `moveReadyCount` / `reviewSignalCount` + toolbar (implements D) |
| NOV-29 | Review-only filter inline guidance (orthogonal) |
| NOV-30 | Primary preview CTA (orthogonal) |

## Acceptance criteria mapping

| AC | Coverage |
|----|----------|
| Written decision in `docs/` | This file |
| Rationale covers PR-19/20 apply constraints | § Rationale vs PR-19 / PR-20 / Finalize |
| B/C/D follow-up linked | B/C rejected; D → NOV-27 |
| Parent NOV-25 후처리 정책 | Hybrid A+D documented; `parent: NOV-25` frontmatter |
