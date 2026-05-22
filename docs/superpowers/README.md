# Superpowers workflow docs

NovelGuard uses [Superpowers](https://github.com/obra/superpowers) skills for process; this folder holds **project-approved** design and implementation artifacts.

## Locations

| Type | Path pattern | When |
|------|----------------|------|
| Design spec | `specs/YYYY-MM-DD-<topic>-design.md` | After `brainstorming`, before implementation |
| Implementation plan | `plans/YYYY-MM-DD-<topic>.md` | After `writing-plans`, before coding |
| Policy entrypoint | [`AGENTS.md`](../../AGENTS.md) | Skill routing and gates |

## Approval gate

1. Write or update spec → human reviews in the spec file → **approved**
2. Write plan → human reviews → **approved**
3. Implement (Persona Dialogue + tests + verification)

Do not skip for non-trivial work. Small one-line fixes may proceed without a new spec if the user says so.

## Historical docs

Older research and plans remain under [`documents/`](../../documents/README.md). **Do not** add new specs or plans there.

## Active artifacts

### Specs

- [2026-05-22-agent-governance-design.md](specs/2026-05-22-agent-governance-design.md)
- [2026-05-22-design-md-ui-rebrand-design.md](specs/2026-05-22-design-md-ui-rebrand-design.md) — DESIGN.md + Calm SaaS rebrand (approved)
- [2026-05-22-layer-seams-and-composition-design.md](specs/2026-05-22-layer-seams-and-composition-design.md)
- [2026-05-22-duplicate-detection-title-blocking-design.md](specs/2026-05-22-duplicate-detection-title-blocking-design.md) — title norm + blocking for updated anthologies (approved)
- [2026-05-22-ui-work-hub-ia-design.md](specs/2026-05-22-ui-work-hub-ia-design.md) — single work screen, minimal nav, global toolbar (approved)

### Plans

- [2026-05-22-agent-governance.md](plans/2026-05-22-agent-governance.md) — governance reorg (implemented 2026-05-22)
- [2026-05-22-design-md-ui-rebrand.md](plans/2026-05-22-design-md-ui-rebrand.md) — DESIGN.md UI rebrand (in progress)
- [2026-05-22-layer-seams-and-composition.md](plans/2026-05-22-layer-seams-and-composition.md)
- [2026-05-22-duplicate-detection-title-blocking.md](plans/2026-05-22-duplicate-detection-title-blocking.md) — title blocking (ready)
- [2026-05-22-ui-work-hub-ia.md](plans/2026-05-22-ui-work-hub-ia.md) — work screen IA (implemented)
