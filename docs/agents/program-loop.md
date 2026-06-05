# Program loop (PR tracks)

Read only when doing roadmap-driven PR work. Short guide: [AGENTS.md](../../AGENTS.md).

## Resolve `current_query`

1. [docs/superpowers/roadmap/README.md](../superpowers/roadmap/README.md) → active roadmap file.
2. First phase-table row not **Done** (top-to-bottom).
3. Tracker (optional): [current_query.md](../superpowers/roadmap/current_query.md).

Require **approved spec** + **approved plan** per PR — not roadmap rows alone.

## Steps 1 → 15

| Step | Action | Output |
|------|--------|--------|
| 1 | Read roadmap | `current_query` PR id |
| 2 | `brainstorming` | intent, constraints, success criteria |
| 3 | `brainstorming` | spec → `docs/superpowers/specs/NNN-…-design.md` |
| 4 | `/grill-me` (self) | lock decisions |
| 5 | `brainstorming` | spec status **approved** |
| 6 | `writing-plans` | plan → `docs/superpowers/plans/NNN-…-prNN-….md` |
| 7 | Plan vs spec | fix gaps |
| 8 | `executing-plans` / `subagent-driven-development` | implement on `feat/prNN-*` or `ai/job-*` |
| 9 | `requesting-code-review` | spec compliance review |
| 10 | `receiving-code-review` | triage feedback |
| 11 | Fix findings | minimal diffs |
| 12 | `/try-and-error-fix` | full matrix green |
| 13 | `finishing-a-development-branch` + `/babysit` | PR merge-ready |
| 14 | Read roadmap | PR **Done**; advance `current_query` |
| 15 | Repeat | until phase table complete |

**Branch:** no commit to `main`/`master` without approval. No "tests passed" without running them.

Deep workflow: [superpowers/agent-workflow.md](../superpowers/agent-workflow.md).
