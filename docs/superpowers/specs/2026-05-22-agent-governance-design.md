# Agent Governance Design

> Status: approved (2026-05-22)
> Supersedes: scattered rules in AGENTS.md + five `alwaysApply: true` Cursor rules

## Problem

- Five Cursor rules all used `alwaysApply: true`, duplicating Persona, planning gates, and verification on every turn.
- AGENTS.md claimed `root.mdc` was canonical while also listing a separate priority order.
- No Superpowers skill routing; planning docs lived only under `documents/` with no `docs/superpowers/` tree.
- Planning workflow overlapped Superpowers `brainstorming` / `writing-plans` without a single gate definition.

## Goals

1. **AGENTS.md** = short cross-agent constitution: identity, instruction priority, Superpowers routing, hard invariants, doc map, verification reporting.
2. **`.cursor/rules/`** = Cursor-specific detail with **only** `00-project-core` and `10-superpowers-routing` as `alwaysApply: true`.
3. **New specs/plans** only under `docs/superpowers/{specs,plans}/`; `documents/` = historical records + `CURSOR_MEMO.md`.
4. Preserve **Persona Dialogue** (Simon → owner → code; Tess → Rex) as communication layer, not a replacement for Superpowers process skills.

## Instruction priority

1. User explicit request in the current session
2. `AGENTS.md`
3. Applicable `.cursor/rules/*.mdc` (glob match)
4. `docs/` and `documents/` (historical)
5. Installed Superpowers skills (when AGENTS routing table applies)
6. General model knowledge

On conflict: stop and report; do not guess.

## Unified planning gate

Non-trivial work:

1. `brainstorming` → design spec in `docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md`
2. Human approval on spec
3. `writing-plans` → plan in `docs/superpowers/plans/YYYY-MM-DD-<topic>.md`
4. Human approval on plan
5. Implementation with Persona Dialogue (briefings immediately before code)
6. `requesting-code-review` when review is requested
7. `finishing-a-development-branch` when work is complete

Do not skip spec/plan gates. Persona briefings do not replace them.

## Cursor rules layout

| File | alwaysApply | Role |
|------|-------------|------|
| `00-project-core.mdc` | true | Facts, verification honesty, approval gate one-liner |
| `10-superpowers-routing.mdc` | true | Skill routing checklist |
| `20-persona-dialogue.mdc` | false | 3-step dialogue, role–layer table |
| `30-novelguard-architecture.mdc` | false | Layers, ports, domain terms |
| `40-testing-gates.mdc` | false | pytest → ruff → mypy → black, verify script |
| `50-docs-governance.mdc` | false | superpowers paths, documents = archive |
| `55-mcp.mdc` | false | MCP when to use / schema / env vars |
| `90-branch-pr-finish.mdc` | false | Branch completion four options |

Remove legacy: `root.mdc`, `persona-dialogue.mdc`, `architecture.mdc`, `cursor-usage.mdc`, `mcp.mdc`.

## Hard invariants (NovelGuard)

- Layer boundaries per `docs/current_architecture.md`; no I/O in domain; no concrete infra imports in application.
- Duplicate cleanup: dry-run preview and user approval before move/delete.
- API secrets in `.env` only.
- Do not claim tests passed without running the exact command.

## Out of scope

- Modifying Superpowers plugin/skills source
- Moving or deleting historical files under `documents/`
- Django/Shapez template rules (wrong project)

## Success criteria

- AGENTS.md under ~100 lines; no MCP table or full command table inlined
- Exactly two `alwaysApply: true` rules in `.cursor/rules/`
- `docs/superpowers/README.md` documents naming and approval flow
- `documents/README.md` states no new specs/plans there
