# Superpowers roadmap

Program-level sequencing and status — **not** implementation detail.

| Artifact | Location | Purpose |
|----------|----------|---------|
| **Roadmap** | `roadmap/NNN-YYYY-MM-DD-<topic>-roadmap.md` | Multi-PR waves, done vs next, dependencies, links to specs/plans |
| **Spec** | `specs/YYYY-MM-DD-<topic>-design.md` | Approved design — human gate before plan |
| **Plan** | `plans/YYYY-MM-DD-<topic>.md` | Task-level execution for one PR slice |

## Workflow

```text
roadmap (orientation) → spec (approve) → plan (approve) → implement → update roadmap status
```

Roadmap entries are **proposed** until a matching spec is approved. Do not treat roadmap PR labels as committed scope without a spec.

## Files

| File | Scope |
|------|--------|
| [000-2026-06-01-novelguard-master-roadmap.md](./000-2026-06-01-novelguard-master-roadmap.md) | PR-0..19 (done); program waves A–G |
| [001-2026-06-02-pr20-pr25-development-roadmap.md](./001-2026-06-02-pr20-pr25-development-roadmap.md) | **Active track:** PR-20..25 — **next:** PR-24 spec `012` (draft) |

## Adding a roadmap file

1. Copy the section template from the bottom of `000-2026-06-01-novelguard-master-roadmap.md`.
2. Name: `NNN-YYYY-MM-DD-<topic>-roadmap.md` (increment `NNN` for a new program track).
3. Link parent spec(s) and child plans as they are written.
4. Update this README table and [../README.md](../README.md).

## Authority

- **Behavior truth:** code + tests + [current_architecture.md](../../current_architecture.md)
- **Done when:** matching plan’s “Implementation status” is **Done** and verification is recorded there
- **Next work:** roadmap proposes order; **spec approval** locks scope
