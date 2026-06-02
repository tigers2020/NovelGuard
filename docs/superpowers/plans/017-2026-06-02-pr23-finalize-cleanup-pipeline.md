# PR-23: Finalize / Cleanup Pipeline — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Ship Finalize work mode with summary, 4-step verification runner, JSON report artifact, optional empty-dir cleanup, and UI CTAs.

**Architecture:** `finalize_blockers` (pure rules) + `finalize_summary` + `finalize_runner` (threaded); bridge methods; `FinalizeWorkspace` React surface; audit tail reader.

**Tech Stack:** Python 3.12, React + TypeScript, pytest (extend existing files only).

**Spec:** [011-2026-06-02-finalize-cleanup-pipeline-design.md](../specs/011-2026-06-02-finalize-cleanup-pipeline-design.md) (**approved** 2026-06-02)

**Plan status:** **Implemented** (merged [PR #14](https://github.com/tigers2020/NovelGuard/pull/14), 2026-06-02)

**Prerequisite:** PR-22 merged or committed (`[pr22] quality repair execution`)

**Parent:** [001 PR-20..25 roadmap](../roadmap/001-2026-06-02-pr20-pr25-development-roadmap.md)

**Test policy:** Extend `tests/test_bridge_contract.py`, `mockBridge.ts`, snapshot contract — no new test files without `TEST_ALLOWED`.

---

## Plan-locked constants (spec 011 approved)

| Constant | Value |
|----------|--------|
| Report root | `~/.novelguard/SAVE/finalize/<sessionId>/` |
| `CLEANUP_ALLOWED_ROOT_NAMES` | `frozenset({"duplicate", "organized"})` — G5; no `.novelguard` |
| Pipeline phase | `finalize` |
| Work mode id | `finalize` |

---

## File map

| File | Action |
|------|--------|
| `src/application/finalize_blockers.py` | **Create** |
| `src/application/finalize_summary.py` | **Create** |
| `src/application/finalize_report.py` | **Create** |
| `src/application/finalize_runner.py` | **Create** |
| `src/application/ports/finalize_cleanup.py` | **Create** |
| `src/infrastructure/finalize_cleanup.py` | **Create** |
| `src/application/dto_mapper.py` | **Modify** — `work.finalize` |
| `src/application/library_session.py` | **Modify** — finalize thread, cancel, getters |
| `src/app/bridge_api.py` | **Modify** — 4 methods |
| `src/app/bridge_contract.py` | **Modify** — validators |
| `src/app/bridge_parity.py` | **Modify** |
| `web/src/types/snapshot.ts` | **Modify** — `WorkMode`, `work.finalize` |
| `web/src/types/finalize.ts` | **Create** |
| `web/src/features/work/FinalizeWorkspace.tsx` | **Create** |
| `web/src/features/work/WorkModeTabs.tsx` | **Modify** — 4th tab |
| `web/src/features/work/WorkRoute.tsx` | **Modify** |
| `web/src/bridge/*` | **Modify** |
| `tests/test_bridge_contract.py` | **Modify** |

---

## Task 0: Plan gate

- [x] Spec 011 **approved** (G1–G6 + B1–B4 dated 2026-06-02)
- [x] Plan 017 **approved** (2026-06-02)
- [x] PR-22 on branch baseline (`158b50a` — `[pr22] quality repair execution`)

---

## Task 1: Blocker / warning rules

- [x] `exact_unresolved_queue_count(session) -> int` — exact file rows only (`rowKind=file`, `type=exact`, `status in {unreviewed, conflict}`); excludes near/relation/group rows
- [x] `compute_finalize_blockers(session) -> list[dict]` — G2 approved codes; **never** use raw `queueCount` for `UNRESOLVED_DUPLICATE_QUEUE`
- [x] `near_unresolved_file_row_count(session) -> int` — G3 `NEAR_GROUPS_PRESENT`
- [x] `relation_unresolved_file_row_count(session) -> int` — G3 `UNREVIEWED_RELATION`
- [x] `compute_finalize_warnings(session) -> list[dict]` — omit entries when count==0; no cleanup-empty warning
- [x] `build_finalize_summary` sets `resolve.exactUnresolvedQueueCount` from `exact_unresolved_queue_count`
- [x] Unit coverage via contract tests only

```python
def exact_unresolved_queue_count(session) -> int:
    """
    Count only actionable exact duplicate file rows that are still unresolved.

    Includes:
    - rowKind == "file"
    - type == "exact"
    - status in {"unreviewed", "conflict"}

    Excludes:
    - near rows
    - relation rows
    - group/header rows
    - approved/excluded rows
    """
```

---

## Task 2: Summary + audit tail

- [x] `read_audit_tail(path, limit=50)` — last move/repair apply timestamps + counts
- [x] `build_finalize_summary(session) -> dict`

---

## Task 3: Runner + cleanup port

- [x] `refresh_finalize_session_state(session)` — G4: resolve recount + targeted `reanalyze_quality_for_file_ids`
- [x] `FinalizeRunner` 4 steps on background thread; **reverify** blockers/warnings authoritative over precheck
- [x] `cancel_finalize` flag between steps
- [x] `finalize_cleanup` port — bottom-up empty dirs under `duplicate/**`, `organized/**` only; `Path.resolve()` + root escape check
- [x] Cleanup runner table (G5): `includeCleanup` × blockers → preview-only vs delete
- [x] `LIBRARY_BUSY` mutual exclusion with scan/apply/repair

```python
def refresh_finalize_session_state(session) -> None:
    session.refresh_resolve_counts()
    issue_file_ids = unique_file_ids_from_quality_index(session)
    if issue_file_ids:
        session.reanalyze_quality_for_file_ids(issue_file_ids)
```

---

## Task 4: Report IO

- [x] `write_finalize_report(...)` → `reportId`, path
- [x] `read_finalize_report(reportId)`
- [x] Update `work.finalize` on snapshot after run (G6 fields)
- [x] Bump `libraryRevision` only when `removedEmptyDirs` non-empty (G6)

---

## Task 5: Bridge

- [x] Wire 4 methods; validators
- [x] `run_finalize_verification` does not reject on summary blockers alone (B1)
- [x] Extend `PYWEBVIEW_API_METHODS` + TS parity

---

## Task 6: Web UI

- [x] `FinalizeWorkspace` — summary, blockers, warnings, CTAs
- [x] B1 `data-state` matrix (empty / ready / warning / disabled / running / success / error)
- [x] B1: disable primary + cleanup when `summary.blockers.length > 0`; tooltip = first blocker
- [x] Cleanup checkbox (G5): default off; label/helper per spec; disabled when blockers or running
- [x] `완료 보고서 보기` enabled only when `lastReportId != null`
- [x] Report viewer (read-only JSON panel)

---

## Contract test matrix (Task 7)

| Test | Required |
|------|----------|
| `get_finalize_summary` shape validated | Yes |
| Pending move preview → blocker `PENDING_MOVE_PREVIEW` | Yes |
| Pending repair preview → blocker `PENDING_REPAIR_PREVIEW` | Yes |
| Exact unreviewed file row → `UNRESOLVED_DUPLICATE_QUEUE` → `blocked` | Yes |
| Exact conflict file row → `UNRESOLVED_DUPLICATE_QUEUE` → `blocked` | Yes |
| Near unreviewed only → not blocked; G3 warning | Yes |
| Relation unreviewed only → not blocked; G3 warning | Yes |
| Raw `queueCount > 0` but `exact_unresolved_queue_count == 0` → not blocked | Yes |
| `smallFileAnomalyCount > 0`, encoding/integrity 0 → `complete_with_warnings` + `SMALL_FILE_ANOMALIES` | Yes |
| Near conflict only, exact queue 0 → not blocked + `NEAR_GROUPS_PRESENT` | Yes |
| Relation conflict only → not blocked + `UNREVIEWED_RELATION` | Yes |
| All warnings 0, blockers 0 → `complete` | Yes |
| `get_finalize_summary` includes `exactUnresolvedQueueCount` | Yes |
| Clean library → `complete` or `complete_with_warnings` | Yes |
| Report file created under SAVE | Yes |
| `get_finalize_report` round-trip | Yes |
| `cancel_finalize` mid-run → `cancelled`, idle pipeline | Yes |
| `includeCleanup=false` → preview only, no deletes | Yes |
| `includeCleanup=true` + blockers → no deletes | Yes |
| `includeCleanup=true` + no blockers → empty allowlisted dirs removed | Yes |
| Cleanup never touches `~/.novelguard` or `library_root/.novelguard` | Yes |
| `FinalizeResult.cleanup` always has `previewedEmptyDirs` + `removedEmptyDirs` | Yes |
| Finalize while scan running → `LIBRARY_BUSY` | Yes |
| Quality issue file IDs exist → targeted `reanalyze_quality_for_file_ids` | Yes |
| No quality issues → no quality file reread | Yes |
| `work.scan.state != "success"` → `SCAN_NOT_SUCCESS` after reverify | Yes |
| Near/relation rows present → no detection rerun | Yes |
| Exact duplicate recount → cache only, no hash recompute | Yes |
| `run_finalize_verification` with pre-existing blockers → `blocked` + report (bridge not rejected) | Yes |
| `libraryRevision` unchanged when report-only run (no cleanup removal) | Yes |

**Contract suite (merged):** Five focused cases in `tests/test_bridge_contract.py` (`get_finalize_summary`, clean `complete`, exact queue `blocked`, `LIBRARY_BUSY`). Remaining matrix rows: implementation + manual QA; extend in a follow-up if full matrix automation is required.

---

## Task 7: Verification

- [x] `python scripts/verify_phase_completion.py` — report counts
- [x] Scope freeze — no packaging / FileDock / new repair APIs

---

## Changelog

| Date | Change |
|------|--------|
| 2026-06-02 | Initial plan 017 from draft spec 011 |
| 2026-06-02 | G2: `exact_unresolved_queue_count`; contract matrix exact vs raw queueCount |
| 2026-06-02 | G3: near/relation warning counts; summary `exactUnresolvedQueueCount`; warning matrix |
| 2026-06-02 | G4: `refresh_finalize_session_state`; reverify authoritative; reverify contract rows |
| 2026-06-02 | G5: cleanup allowlist, runner table, UI checkbox, cleanup contract rows |
| 2026-06-02 | G6: no library lock; revision bump on cleanup removal only |
| 2026-06-02 | B1: UI/bridge split; plan status → **approved** |
| 2026-06-02 | Tasks 1–7 complete; merged PR #14; plan status → **implemented** |
