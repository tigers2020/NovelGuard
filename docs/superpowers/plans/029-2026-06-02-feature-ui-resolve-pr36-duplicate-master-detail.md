# PR-36: Duplicate Master-Detail — Implementation Plan

**Spec:** [021 LOCK-33-4](../specs/021-2026-06-02-feature-fullstack-shell-ia-reconciliation-design.md) + [006 duplicate group detail](../specs/006-2026-06-01-duplicate-group-detail-design.md)

**Goal:** Stable Resolve master-detail: row click loads detail; near/relation review-only; responsive detail sheet on narrow viewports.

**Plan status:** Complete (2026-06-03)

---

## Tasks

- [x] Split master row select vs batch checkbox in `ResolveAndOrganizeWorkspace` + grid column
- [x] Harden `DetailPanel` (type badges, review-only banner, keeper disabled when review-only)
- [x] Responsive detail sheet (`lg:` side panel, overlay below)
- [x] Extend `bridgeParity.test.ts` for `getDuplicateGroupDetail`
- [x] Fix `mockDuplicateGroupDetail` row-id + near/relation typing for mock dev
- [x] `npm run lint` + `npm run test` — 76/76

---

## Implementation status

**Done** (2026-06-03) — see roadmap [pre-PR-37 gate](../roadmap/003-2026-06-02-platform-release-gate-roadmap.md#pre-pr-37-gate-track-cleanup--2026-06-03).
