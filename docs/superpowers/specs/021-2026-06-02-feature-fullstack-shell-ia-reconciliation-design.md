---
title: IA Reconciliation — Hybrid 3-Mode + Finalize Subflow
status: approved
approved: 2026-06-03
risk: breaking
grill_me: 2026-06-02
date: 2026-06-02
authors: PR-33 IA gate review (Q1–Q3 grill-me)
parent_spec: docs/superpowers/specs/000-2026-06-01-novelguard-ui-overhaul-design.md
related_specs:
  - docs/superpowers/specs/011-2026-06-02-finalize-cleanup-pipeline-design.md
  - docs/superpowers/specs/018-2026-06-02-feature-ui-shell-work-mode-tab-transition-design.md
  - docs/superpowers/specs/019-2026-06-02-feature-ui-shell-scan-folder-picker-ui-design.md
roadmap: docs/superpowers/roadmap/003-2026-06-02-platform-release-gate-roadmap.md
pr_label: PR-33
plan: docs/superpowers/plans/027-2026-06-02-feature-fullstack-shell-pr33-ia-reconciliation.md
---

# 021 — IA Reconciliation (Hybrid 3-Mode + Finalize Subflow)

## Status

**Approved** (2026-06-03) — grill-me Q1–Q3 complete; **LOCK-33-1..13** and **LOCK-33-MVP-1..6** locked below. Plan [027](../plans/027-2026-06-02-feature-fullstack-shell-pr33-ia-reconciliation.md) complete; PR-34+ implementation per downstream plans.

**Scope sentence:** Reconcile approved Spec 000 **Hybrid 3-mode** IA with current implementation residue (4th `finalize` tab, step-like navigation). Publish authoritative UX locks for PR-34..37. **Docs + IA decision PR** — no layout implementation unless an explicit spike is approved in plan 027.

**Supersedes (UX navigation only):** Spec 011 row “WorkMode **`finalize`** (4th tab)”. Backend finalize capability from Spec 011 / PR-23 remains authoritative.

---

## Problem

| Source | State |
|--------|--------|
| Spec 000 (approved) | **3 modes:** Scan · Resolve & Organize · Quality; subflow-only wizard |
| Spec 011 (approved) | Finalize as **4th WorkMode tab** (implementation-era lock) |
| Current UI | `WorkModeTabs` lists **4 tabs** including `finalize`; `WorkRoute` mounts `FinalizeWorkspace` as a mode panel |
| Spec 018 (approved) | Keep-alive for **4 panels** — assumes 4-mode routing |

The 4th tab reads as wizard-step residue and blocks a clean Hybrid IA. Finalize **capability** (verification runner, cleanup v1, report) must be preserved — only the **navigation surface** changes.

---

## Decision summary

| Topic | Lock |
|-------|------|
| Top-level IA | **Hybrid reconcile (Spec 000)** — 3 modes only |
| Quality | **Top-level mode retained** — not absorbed into Resolve |
| Finalize | **Not a WorkMode** — `FinalizeSubflowDialog` (+ optional nudge from Apply/Repair done) |
| PR-34 scope | **3-mode shell cleanup** — not work-hub single scroll |
| MVP cut | **3B Standard** — PR-33, 34, 36, 37, and PR-42 **or** PR-43 |

---

## Locked decisions — IA (grill-me Q1)

### LOCK-33-1..6 — verbatim

```text
LOCK-33-1
Top-level Work IA is exactly 3 modes:
scan, resolve, quality.

LOCK-33-2
finalize is not a WorkMode.
No top-level finalize tab, route, persistent mode, or sidebar item.

LOCK-33-3
Apply / finalize / repair / UTF-8 conversion are subflows.
They may be dialogs, sheets, drawers, or inline task panels, but not primary navigation modes.

LOCK-33-4
Resolve mode owns duplicate review + organize/move planning.
Move is not a separate top-level mode.

LOCK-33-5
Quality mode owns integrity, encoding analysis, repair eligibility, and issue review.
Finalize may call quality verification but does not own a top-level tab.

LOCK-33-6
PR-33 is IA/spec reconciliation only unless explicitly approved.
Implementation PR starts after spec 021 + plan 027 approval.
```

### Target mode tabs (post PR-34)

```ts
const tabs = [
  { id: "scan", label: "스캔" },
  { id: "resolve", label: "검토 · 정리" },
  { id: "quality", label: "품질" },
];
```

---

## Locked decisions — Finalize placement (grill-me Q2)

### LOCK-33-7..12 — verbatim

```text
LOCK-33-7
Spec 011 "WorkMode finalize" UX lock is superseded by Spec 021.
Backend finalize capability remains valid:
runner, cleanup v1, verification, report, bridge methods, and audit behavior are unchanged.
Only the navigation surface changes:
finalize is a subflow, not a WorkMode.

LOCK-33-8
Finalize UX is FinalizeSubflowDialog or equivalent sheet.
It must not be represented as a top-level WorkMode, tab, route, sidebar item, or persisted selected mode.

LOCK-33-9
Finalize is library-wide verification/cleanup/report.
It is not selection-scoped duplicate apply, move apply, or repair apply.

LOCK-33-10
FinalizeSubflowDialog v1 entry points are exhaustive:
1. Resolve workspace — "최종 검증" CTA or blocker-aware banner
2. Quality workspace — "검증" CTA or post-repair CTA
3. ApplySubflowDialog done panel — optional "최종 검증 계속"
4. RepairSubflowDialog done panel — optional "최종 검증 계속"

LOCK-33-11
No GlobalCommandBar, sidebar, FileSummaryStrip, or shell-level primary finalize CTA in MVP.
Those are deferred unless a later product spec explicitly overrides this.

LOCK-33-12
FinalizeSubflowDialog may reuse FinalizeWorkspace capability, but must not reuse WorkMode routing semantics.
Implementation may extract shared finalize content into a route-free component.
```

### Subflow inventory (canonical)

| Subflow | Trigger | UI | Steps (v1) |
|---------|---------|-----|------------|
| Move / batch apply | Resolve — `이동 계획 미리보기` | `ApplySubflowDialog` (App-level) | preview → confirm → apply → done |
| Quality repair | Quality — repair CTA | `RepairSubflowDialog` | per Spec 010 |
| Finalize verification | Resolve / Quality / Apply done / Repair done | **`FinalizeSubflowDialog`** (new) | summary → blockers/warnings → cleanup opt-in → run → report |
| Full pipeline auto-run | GlobalCommandBar | `PreflightPipelineDialog` + stub | unchanged; not finalize |

Progress during subflow runs: **GlobalCommandBar only** (Spec 000).

---

## Locked decisions — PR-34 scope (grill-me Q3)

### LOCK-33-13 — verbatim

```text
LOCK-33-13
PR-34 is 3-mode shell cleanup, not Work-hub single-scroll scaffold.

Scope:
- remove finalize tab/route
- narrow WorkMode type to scan | resolve | quality
- remove finalize persisted mode handling
- clean WorkModeTabs / routing assumptions
- polish mode shell only as needed

Out of scope:
- no vertical hub scroll
- no section collapse system
- no global FileDock relocation
- no Scan section reassembly
- no Logs/Settings polish
```

**Note on Spec 018:** LOCK-18-4 (4 keep-alive panels) is superseded for panel count — PR-34 reduces to **3 panels**. Optimistic sync and CSS keep-alive pattern remain; adjust plan 024 / PR-34 spec 022 accordingly.

---

## Locked decisions — MVP cut (grill-me Q3)

### LOCK-33-MVP-1..6 — verbatim

```text
LOCK-33-MVP-1
Minimum MVP includes:
PR-33, PR-34, PR-36, PR-37, and exactly one stabilization PR from PR-42 or PR-43.

LOCK-33-MVP-2
PR-35 Scan section reassembly is deferred from MVP.
Reason: PR-32 scan folder picker provides sufficient scan entry for MVP.

LOCK-33-MVP-3
PR-36 Duplicate master-detail remains in MVP.
Reason: duplicate review is the core Resolve path; current vertical stack/evidence UX is a primary usability blocker.

LOCK-33-MVP-4
PR-37 is required for MVP.
Reason: FinalizeSubflowDialog implements LOCK-33-8 through LOCK-33-12 and removes the functional need for a top-level finalize tab.

LOCK-33-MVP-5
PR-38 FileDock, PR-39 Logs, PR-40 Settings, PR-41 full finalize debt, PR-44 packaging, and PR-45 beta/release gate are post-MVP.

LOCK-33-MVP-6
PR-41 may contribute only a thin stabilization subset if it is merged into PR-37 or PR-42/43 scope.
Full PR-41 cleanup debt remains post-MVP unless explicitly re-approved.
```

### MVP path

```text
MVP path:
  PR-33  Spec 021 IA reconciliation (this spec)
  PR-34  3-mode shell cleanup
  PR-36  Duplicate master-detail / Resolve core UX
  PR-37  FinalizeSubflowDialog + move/finalize integration
  PR-42 or PR-43  Stabilization (exactly one)

Deferred:
  PR-35, PR-38, PR-39, PR-40, PR-41 full, PR-44, PR-45
```

---

## Supersession table

| Prior lock | Document | Spec 021 action |
|------------|----------|-----------------|
| WorkMode **`finalize`** (4th tab) | Spec 011 | **Superseded** — UX navigation only |
| 4 keep-alive panels | Spec 018 LOCK-18-4 | **Amended** — 3 panels after PR-34 |
| Work hub single-scroll scaffold | Roadmap 003 PR-34 (proposed) | **Narrowed** — LOCK-33-13 |
| Scan section in MVP | Roadmap 003 PR-35 | **Deferred** — LOCK-33-MVP-2 |

**Unchanged:** Spec 011 G1–G6, B1–B4 (runner, blockers, warnings, cleanup v1, report paths); bridge methods `get_finalize_summary`, `run_finalize_verification`, `get_finalize_report`, `cancel_finalize`; `work.finalize` snapshot slice (status/report metadata — not a mode selector).

---

## Bridge / contract impact (PR-34+)

| Area | PR-33 (this spec) | PR-34+ |
|------|-------------------|--------|
| `WorkMode` type | Document narrowing | Remove `"finalize"` from TS + mock + Python `set_work_mode` validation |
| `setWorkMode("finalize")` | Forbidden by LOCK-33-2 | Remove or reject with clear error |
| `work.finalize` snapshot | Keep | Keep — subflow reads status/report |
| Finalize bridge methods | Keep | Keep — `FinalizeSubflowDialog` callers |
| E2E / contract tests | Note drift | Update in PR-34 / PR-42 |

**Risk:** `breaking` — WorkMode union and mode-tab E2E selectors change. No destructive file mutation in this spec.

---

## Downstream PR scope notes

PR-34..37 specs **must reference** LOCK-33 IDs they implement.

| PR | Delivers | Key locks |
|----|----------|-----------|
| **PR-34** | 3-mode shell cleanup | LOCK-33-1, 2, 13; amend LOCK-18-4 panel count |
| **PR-35** | Scan section (post-MVP) | LOCK-33-MVP-2 defer |
| **PR-36** | Duplicate master-detail | LOCK-33-4; MVP required |
| **PR-37** | FinalizeSubflowDialog + move inline | LOCK-33-7..12; LOCK-33-MVP-4 |
| **PR-42 or PR-43** | Stabilization gate | LOCK-33-MVP-1 |

Proposed downstream spec filenames (roadmap 003 — not committed until each spec is approved):

- `specs/022-…-work-hub-shell-design.md` → rename topic to **3-mode shell cleanup** in body
- `specs/025-…-move-finalize-integration-design.md` → FinalizeSubflowDialog primary deliverable

---

## Wireframe — Work route (post PR-34)

```text
┌─────────────────────────────────────────────────────────────┐
│ WorkModeTabs: [ 스캔 ] [ 검토·정리 ] [ 품질 ]                  │
├─────────────────────────────────────────────────────────────┤
│ Active mode workspace (keep-alive × 3)                       │
│   scan    → ScanWorkspace (+ PR-32 folder picker)            │
│   resolve → ResolveAndOrganizeWorkspace                      │
│   quality → QualityWorkspace                                 │
└─────────────────────────────────────────────────────────────┘

Subflows (overlay / dialog — not tabs):
  ApplySubflowDialog, RepairSubflowDialog, FinalizeSubflowDialog (PR-37)
```

Shell-level: `ShellFileDock`, `GlobalCommandBar` — no MVP finalize CTA (LOCK-33-11).

---

## Out of scope (PR-33)

- Implementing PR-34..37 layouts or components
- Backend pipeline / detection changes
- New bridge methods
- Scan section reassembly (PR-35 defer)
- Logs / Settings / FileDock polish (PR-38..40 defer)
- Full PR-41 finalize debt

---

## Acceptance gate

- [x] Human approval of this spec (021) — 2026-06-03
- [x] Plan 027 approved — 2026-06-03
- [x] Roadmap 003 phase index updated with LOCK-33 MVP amend — 2026-06-03
- [x] PR-34/36 scope covered by this spec + plans 028/029 (dedicated specs 022/024 optional)
- [ ] Spec 025 (move/finalize integration) on write for PR-37 — or fold into plan 030

---

## Grill-me log

| Q | Topic | Answer | Date |
|---|--------|--------|------|
| Q1 | Top-level IA | **C — Hybrid reconcile**; Quality retained; finalize tab removed | 2026-06-02 |
| Q2 | Finalize placement | **2B + 2A nudge** — `FinalizeSubflowDialog` + Apply/Repair done CTA | 2026-06-02 |
| Q3 | MVP cut | **3B Standard** — IN 33,34,36,37,42\|43; OUT 35,38-41 full,44,45 | 2026-06-02 |

---

## References

- [000 UI overhaul](./000-2026-06-01-novelguard-ui-overhaul-design.md)
- [011 Finalize pipeline](./011-2026-06-02-finalize-cleanup-pipeline-design.md)
- [018 Work mode transitions](./018-2026-06-02-feature-ui-shell-work-mode-tab-transition-design.md)
- [003 Release gate roadmap](../roadmap/003-2026-06-02-platform-release-gate-roadmap.md)
