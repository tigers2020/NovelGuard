# Superpowers roadmap

Program-level sequencing and status — **not** implementation detail.

| Artifact | Location | Purpose |
|----------|----------|---------|
| **Roadmap** | `roadmap/NNN-YYYY-MM-DD-<area>-<topic>-roadmap.md` | Multi-PR waves, done vs next, dependencies, links to specs/plans |
| **Spec** | `specs/NNN-YYYY-MM-DD-<kind>-<layer>-<area>-<topic>-design.md` | Approved design — human gate before plan |
| **Plan** | `plans/NNN-YYYY-MM-DD-<kind>-<layer>-<area>-prNN-<topic>.md` | Task-level execution for one PR slice |

Full taxonomy (`kind`, `layer`, `area`, `risk`, directory-local `NNN`): [agent-workflow.md § Spec & plan file naming](../agent-workflow.md#spec--plan-file-naming).

## Workflow

```text
roadmap (orientation) → spec (approve) → plan (approve) → implement → update roadmap status
```

Roadmap entries are **proposed** until a matching spec is approved. Do not treat roadmap PR labels as committed scope without a spec.

## Files

| File | Scope |
|------|--------|
| [000-2026-06-01-novelguard-master-roadmap.md](./000-2026-06-01-novelguard-master-roadmap.md) | PR-0..19 (done); program waves A–G |
| [001-2026-06-02-pr20-pr25-development-roadmap.md](./001-2026-06-02-pr20-pr25-development-roadmap.md) | Closed track: PR-20..25 **Done** |
| [002-2026-06-02-pr26-pr30-platform-polish-roadmap.md](./002-2026-06-02-pr26-pr30-platform-polish-roadmap.md) | **Closed track:** PR-26..32 **Done** |
| [003-2026-06-02-platform-release-gate-roadmap.md](./003-2026-06-02-platform-release-gate-roadmap.md) | **Closed:** PR-33..45 — verify 7/7 on main (2026-06-03) |
| [004-2026-06-03-post-release-beta-roadmap.md](./004-2026-06-03-post-release-beta-roadmap.md) | **Closed:** automated beta gate (2026-06-03) |

## Adding a roadmap file

1. Copy the section template from the bottom of `000-2026-06-01-novelguard-master-roadmap.md`.
2. Name: `NNN-YYYY-MM-DD-<area>-<topic>-roadmap.md` (`NNN` = highest in `roadmap/` + 1).
3. Link parent spec(s) and child plans as they are written.
4. Update this README table and [../README.md](../README.md).

## Authority

- **Behavior truth:** code + tests + [current_architecture.md](../../current_architecture.md)
- **Done when:** matching plan’s “Implementation status” is **Done** and verification is recorded there
- **Next work:** roadmap proposes order; **spec approval** locks scope
