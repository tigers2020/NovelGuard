# Superpowers roadmap

Program-level sequencing and status — **not** implementation detail.

| Artifact | Location | Purpose |
|----------|----------|---------|
| **Kanban** | [Kanban Markdown board](../../agent/KANBAN.md) (`.devtool/features/`) | PR **status/column**, spec/plan links, active track |
| **Roadmap** | `roadmap/NNN-YYYY-MM-DD-<area>-<topic>-roadmap.md` | Sequencing narrative, scope sections, dependencies |
| **Spec** | `specs/NNN-YYYY-MM-DD-<kind>-<layer>-<area>-<topic>-design.md` | Approved design — human gate before plan |
| **Plan** | `plans/NNN-YYYY-MM-DD-<kind>-<layer>-<area>-prNN-<topic>.md` | Task-level execution for one PR slice |

Full taxonomy (`kind`, `layer`, `area`, `risk`, directory-local `NNN`): [agent-workflow.md § Spec & plan file naming](../agent-workflow.md#spec--plan-file-naming).

## Workflow

```text
roadmap (orientation) → spec (approve) → plan (approve) → implement → move kanban card
```

Kanban cards are **proposed** until a matching spec is approved. Do not treat kanban/roadmap PR labels as committed scope without a spec.

## Files

| File | Scope |
|------|--------|
| [000-2026-06-01-novelguard-master-roadmap.md](./000-2026-06-01-novelguard-master-roadmap.md) | PR-0..19 (done); program waves A–G |
| [001-2026-06-02-pr20-pr25-development-roadmap.md](./001-2026-06-02-pr20-pr25-development-roadmap.md) | **Closed:** PR-20..25 **Done** |
| [002-2026-06-02-pr26-pr30-platform-polish-roadmap.md](./002-2026-06-02-pr26-pr30-platform-polish-roadmap.md) | **Closed track:** PR-26..32 **Done** |
| [003-2026-06-02-platform-release-gate-roadmap.md](./003-2026-06-02-platform-release-gate-roadmap.md) | **Closed:** PR-33..45 — verify 7/7 on main (2026-06-03) |
| [004-2026-06-03-post-release-beta-roadmap.md](./004-2026-06-03-post-release-beta-roadmap.md) | **Closed:** automated beta gate (2026-06-03) |
| [005-2026-06-03-ops-automation-roadmap.md](./005-2026-06-03-ops-automation-roadmap.md) | **Closed:** Hermes + worker + beta smokes + CI (2026-06-03) |
| [006-2026-06-03-product-backlog-roadmap.md](./006-2026-06-03-product-backlog-roadmap.md) | **Superseded** → 007 |
| [007-2026-06-03-pr48-pr57-post-beta-roadmap.md](./007-2026-06-03-pr48-pr57-post-beta-roadmap.md) | **Active:** PR-48..57 post-beta product wave |

## Adding a roadmap file

1. Copy the section template from the bottom of `000-2026-06-01-novelguard-master-roadmap.md`.
2. Name: `NNN-YYYY-MM-DD-<area>-<topic>-roadmap.md` (`NNN` = highest in `roadmap/` + 1).
3. Link parent spec(s) and child plans as they are written.
4. Update this README table and [../README.md](../README.md).

## Authority

- **Behavior truth:** code + tests + [current_architecture.md](../../current_architecture.md)
- **Done when:** matching plan’s “Implementation status” is **Done** and verification is recorded there
- **Next work:** roadmap proposes order; **spec approval** locks scope
