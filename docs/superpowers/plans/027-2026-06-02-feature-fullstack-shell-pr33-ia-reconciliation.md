# PR-33: IA Reconciliation — Implementation Plan

**Spec:** [021 ia-reconciliation](../specs/021-2026-06-02-feature-fullstack-shell-ia-reconciliation-design.md) (**approved** 2026-06-03)

**Goal:** Lock Hybrid 3-mode IA + FinalizeSubflowDialog placement (LOCK-33-1..13, LOCK-33-MVP-1..6). **Docs-only** — no layout implementation.

**Scope:** Spec 021 approval, supersession notes, roadmap 003 status. No `web/` or `src/` product code unless an approved spike is added (none).

**Plan status:** Complete (2026-06-03)

---

## Implementation status

**Done** (2026-06-03) — spec 021 approved; supersession notes in 011/018; roadmap 003 updated.

---

## Tasks

### Task 1: Approve spec 021

- [x] Set spec 021 `status: approved` and check acceptance gate items owned by this PR
- [x] LOCK-33 IDs remain verbatim in spec body

### Task 2: Supersession cross-links

- [x] Spec 011 — note Spec 021 supersedes WorkMode `finalize` tab (UX only)
- [x] Spec 018 — amend LOCK-18-4 panel count to 3 after PR-34 (reference LOCK-33-13)

### Task 3: Roadmap + index

- [x] Roadmap 003 — PR-33 **Done**; PR-34 **Next**
- [x] [superpowers README](../README.md) — active spec → 022 (on write) / PR-34 in progress note

### Task 4: Verification

- [x] Docs-only — no pytest/npm required for this plan slice

---

## Acceptance mapping

| Spec gate | Task |
|-----------|------|
| Human approval 021 | 1 |
| Plan 027 approved | this file |
| Roadmap 003 updated | 3 |
| Downstream specs reference LOCK-33 on write | PR-34+ (plan 028) |

---

## Out of scope

- PR-34..37 implementation
- New bridge methods
- FinalizeSubflowDialog component (PR-37)

---

## PR description snippet

```text
[pr33] Approve IA reconciliation spec 021 (LOCK-33)

- Hybrid 3-mode + FinalizeSubflowDialog locks
- Supersede Spec 011 finalize tab UX; amend Spec 018 panel count
- Roadmap 003 PR-33 done
```
