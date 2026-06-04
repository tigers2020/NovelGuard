# Agent Runbook

Non-roadmap agent execution: one ticket per run, explicit stop conditions, structured output.

**Kanban gates apply to all work.** See [AGENTS.md](../../AGENTS.md) and `.cursor/rules/20-kanban-workflow.mdc`.

---

## Source of truth

| Work type | Ticket source | Approval gate |
|-----------|---------------|---------------|
| Roadmap PR / features | `.devtool/features/` card `status` + [KANBAN.yml](./KANBAN.yml) + [current_query.md](../superpowers/roadmap/current_query.md) | Column gates; spec + plan approved before **ready** |
| Small / hotfix / docs | Kanban card + [BACKLOG.yml](./BACKLOG.yml) | Card at **ready**/**in-progress**; `acceptance` + `files_allowed` |
| Shared procedure | This file | — |
| Run state | [AGENT_STATE.json](./AGENT_STATE.json) | — |

---

## Load order

1. Read `AGENTS.md` and `.cursor/rules/20-kanban-workflow.mdc`.
2. Read the active card in `.devtool/features/` (create at **triage** if missing).
3. **Only act for the card’s current column** (see [KANBAN.md](./KANBAN.md)).
4. Read [KANBAN.yml](./KANBAN.yml) meta and [current_query.md](../superpowers/roadmap/current_query.md) for roadmap PRs.
5. Read linked spec/plan paths from the card when column is **plan** or later.
6. For BACKLOG-only items: still require a kanban card; do not bypass **spec**/**plan** gates for roadmap-sized scope.
7. Read [BUGS.yml](./BUGS.yml), [CHANGELOG-agent.md](./CHANGELOG-agent.md), indexes as needed.

---

## Execution rule

- Work on **exactly one scheduled item** per run unless the user requests parallel work.
- **Loop mode** (automation): max **3** scheduled items per invocation; re-run tests between items.
- Print a rule **checklist** (applied / N/A / conflict) including **kanban column**.
- Before editing: planned files + **current column → target column**.
- **No `src/`/`web/` edits** unless card is **ready** or **in-progress** (after **ready** gate).
- After editing: run tests or report why not.
- Move the kanban card when the column exit gate is met; `python scripts/sync_kanban_folders.py` if needed.
- Update `CHANGELOG-agent.md`, `AGENT_STATE.json`, `BUGS.yml` as appropriate.

---

## Stop conditions

Stop immediately and report `BLOCKED` or `FAILED` if:

- card column does not allow the requested action (e.g. code while in **spec**)
- required spec is not **approved** (before **plan** or later)
- required plan is not **approved** (before **todo** or later)
- card not **ready** but implementation was requested
- more than one **scheduled** item started without user approval
- selected ticket has no `acceptance` criteria
- conflict with `RULES.md` or `AGENTS.md`
- path outside `files_allowed` or inside `files_forbidden`
- tests / lint / typecheck fail
- P0/P1 bug blocks the ticket
- cannot update `CHANGELOG-agent.md` or `AGENT_STATE.json`

---

## Required output

Every run must print:

1. **Kanban column** at start (and at end if changed)
2. Active card id / title
3. Rule checklist (digest)
4. Files planned
5. Files changed
6. Tests run (command + exit code)
7. Bugs found (if any)
8. Changelog / state updates
9. **Next column** the user or agent should target

Automated jobs: **status**, **column**, **changed paths**, **verification**, **blockers**, **next action** per `AGENTS.md`.
