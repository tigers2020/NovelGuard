# PR-22: Quality Repair Execution — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship UTF-8 repair for `invalid_utf8` via frozen-plan preview token, detail-only UI (single issue), atomic rewrite with fileId backup, audit, and file-scoped re-analyze.

**Architecture:** `build_quality_repair_plan` + `QualityRepairGuard` (frozen plan); `FilesystemRepairPort`; three bridge methods; `RepairSubflowDialog`; encoding strict + low-confidence `iso-8859-1`.

**Tech Stack:** Python 3.12 (stdlib encodings), React + TypeScript, pytest (extend existing files only).

**Spec:** [010-2026-06-02-quality-repair-execution-design.md](../specs/010-2026-06-02-quality-repair-execution-design.md) (**approved** 2026-06-02)

**Plan status:** **Implemented** (2026-06-02) — pytest 82 contract tests pass; ruff fix; web lint pass.

**Prerequisite:** PR-21 committed (`[pr21] quality issue detail response and drawer UX`) — eligibility `eligible: false` baseline fixed before PR-22 flips.

**Parent:** [001 PR-20..25 roadmap](../roadmap/001-2026-06-02-pr20-pr25-development-roadmap.md)

**Test policy:** Extend `tests/test_bridge_contract.py`, `mockBridge.ts` — no new test files without `TEST_ALLOWED`.

---

## Plan-locked constants (spec-approved)

| Constant | Value |
|----------|--------|
| `MAX_REPAIR_BATCH` | `10` |
| High-confidence encodings | `cp949`, `euc-kr`, `shift_jis` (strict) |
| Low-confidence fallback | `iso-8859-1` (strict; preview warning required) |
| `TEMP_SUFFIX` | `.novelguard-repair.tmp` |
| Backup root | `SAVE/repair_backup/<sessionId>/<fileId>/` |

---

## File map

| File | Action |
|------|--------|
| `src/domain/repair_models.py` | **Create** — `RepairOperation`, confidence field |
| `src/application/repair_plan_fingerprint.py` | **Create** |
| `src/application/encoding_detect.py` | **Create** — strict + high/low confidence |
| `src/application/build_quality_repair_plan.py` | **Create** — mixed selection reject |
| `src/application/apply_quality_repair.py` | **Create** — B5 sequence |
| `src/application/quality_issue_detail.py` | **Modify** — `eligible: true` for repairable `invalid_utf8` |
| `src/application/ports/filesystem_repair.py` | **Create** |
| `src/infrastructure/filesystem_repair.py` | **Create** |
| `src/app/quality_repair_guard.py` | **Create** — `PendingQualityRepair` frozen plan |
| `src/app/bridge_api.py` | **Modify** — mutual exclusion both directions |
| `src/app/bridge_contract.py` | **Modify** — preview vs apply error codes |
| `web/src/types/qualityRepair.ts` | **Create** |
| `web/src/features/work/RepairSubflowDialog.tsx` | **Create** |
| `web/src/features/work/QualityWorkspace.tsx` | **Modify** — detail-only entry |
| `tests/test_bridge_contract.py` | **Modify** — matrix below |

---

## Task 0: Plan gate checklist

- [x] Spec 010 **approved** (2026-06-02) — G1–G6 + B1–B5 + LOCK-1..10.
- [x] Plan 016 **approved** (2026-06-02).
- [x] PR-21 committed on branch (baseline `eligible: false`).
- [ ] Implementation approved — proceed Tasks 1–8.

---

## Contract test matrix (Task 8 — required)

| Test | Required |
|------|----------|
| PR-21 baseline: `invalid_utf8` detail `eligible: false` before PR-22 eligibility change reverted in same test session | Yes |
| After PR-22: `invalid_utf8` detail `eligible: true` | Yes |
| `empty_file` / `tiny_file` / `read_error` repair preview reject (`MIXED_OR_INELIGIBLE_SELECTION`) | Yes |
| Mixed eligible + ineligible ids in one preview → reject | Yes |
| `len(issueIds) > 10` → `BATCH_LIMIT_EXCEEDED` | Yes |
| Move pending blocks repair preview/apply | Yes |
| Repair pending blocks move preview/apply | Yes |
| Stale `libraryRevision` → `STALE_REPAIR_PREVIEW` | Yes |
| Stale file bytes (hash/size) → `STALE_REPAIR_PREVIEW`; original unchanged | Yes |
| `cp949` strict repair success | Yes |
| `euc-kr` strict repair success | Yes |
| `shift_jis` strict repair success | Yes |
| `iso-8859-1` only → preview `encodingConfidence: low` + warning | Yes |
| Backup `original.bin` + `metadata.json` before replace | Yes |
| Temp replace failure → original bytes intact | Yes |
| Successful apply → file-scoped re-analyze; encoding issue gone | Yes |
| Partial batch: first ok second fail → `REPAIR_FAILED`, first file repaired, revision bumped | Yes |
| Audit: `repair_preview_created`, `repair_applied`, `repair_failed` | Yes |

---

## Task 1: Domain + frozen fingerprint

- [ ] `RepairOperation` with `fileId`, `encodingConfidence`, identity fields per spec B2.
- [ ] `repair_plan_fingerprint` — canonical JSON parity PR-15.

---

## Task 2: Encoding detection (B1)

- [ ] `detect_encoding(data) -> (encoding, confidence) | None` — high candidates first, then iso-8859-1 low only.
- [ ] Strict decode only; no silent latin-1 as high.

---

## Task 3: Planner + guard

- [ ] `issue_selection_fingerprint` — sorted ids.
- [ ] `PendingQualityRepair` stores sessionId, revision, fingerprints, operations.
- [ ] Preview **rejects** mixed/ineligible/`>10`/empty (no skip path).
- [ ] `MOVE_PREVIEW_ACTIVE` / replace prior repair pending on new preview.

---

## Task 4: Apply + backup (B3, B4, B5)

- [ ] fileId backup dirs + metadata.json.
- [ ] 14-step apply sequence; temp same directory; replace failure safe.
- [ ] Partial semantics LOCK-9; `REPAIR_FAILED` details.
- [ ] File-scoped re-analyze + revision bump.

---

## Task 5: Bridge + contract

- [ ] Split `RepairPreviewErrorCode` / `RepairApplyErrorCode` validators.
- [ ] Symmetric `REPAIR_PREVIEW_ACTIVE` on move path.
- [ ] Eligibility flip in `quality_issue_detail` (PR-22 only).

---

## Task 6–7: Web

- [ ] Types + fingerprint + mockBridge.
- [ ] `RepairSubflowDialog` — single `issueIds[0]`; low-confidence warning UI.
- [ ] No repair-all control.

---

## Task 8: Verification

- [ ] Implement contract test matrix above in `test_bridge_contract.py`.
- [ ] `python scripts/verify_phase_completion.py` — report counts.

---

## Scope freeze

No finalize, packaging, FileDock, PR-21 shape changes, or repair-all UI.

---

## Changelog

| Date | Change |
|------|--------|
| 2026-06-02 | Initial plan 016 |
| 2026-06-02 | Grill-me locks; test matrix; **approved** |
