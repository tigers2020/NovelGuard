# AGENTS.md

Canonical entry for **humans, Cursor IDE, Cursor CLI runners, and Cloud Automations** on NovelGuard.

**Deep automation:** [docs/agent-automation.md](docs/agent-automation.md)  
**Superpowers workflow (large work):** [docs/superpowers/agent-workflow.md](docs/superpowers/agent-workflow.md)  
**Kanban processing (all work):** [docs/agent/KANBAN.md](docs/agent/KANBAN.md) · rule `.cursor/rules/20-kanban-workflow.mdc`

---

## Project

NovelGuard — local-first novel scan, duplicate detection, review, and cleanup.

Stack: Python 3.12+ (`src/`), React+TS (`web/`), Tailwind v4 ([DESIGN.md](DESIGN.md)).  
Layers: `domain` → `application` → `infrastructure` → `web` → `app` ([docs/current_architecture.md](docs/current_architecture.md)).

**Safety:** No destructive file moves without dry-run preview + user approval. Logs/reports are not duplicate-detection inputs unless a spec says so.

---

## Instruction priority

On conflict, stop and report.

1. Explicit user / job message for this run  
2. This `AGENTS.md`  
3. Kanban column gates (`.cursor/rules/20-kanban-workflow.mdc`)  
4. Task spec under `docs/superpowers/specs/` (when named)  
5. General model knowledge  

Opt-in unless requested: `persona/`, legacy `protocols/`, Superpowers ceremony.

---

## Kanban-first processing (default)

**Every user requirement is processed through the kanban board**, not ad-hoc coding.

| Artifact | Location |
|----------|----------|
| Board (status truth) | `.devtool/features/<status>/*.md` — [Kanban Markdown](docs/agent/KANBAN.md) |
| Meta (track, current PR) | [docs/agent/KANBAN.yml](docs/agent/KANBAN.yml) |
| Active slice pointer | [docs/superpowers/roadmap/current_query.md](docs/superpowers/roadmap/current_query.md) |
| Specs / plans | `docs/superpowers/specs/`, `docs/superpowers/plans/` |

### When the user asks for work

1. **Locate the card** for that slice (or create one at **triage**).  
2. **Read `status`** — that column is the only phase you may advance this run.  
3. **Perform column-allowed work** (see table below).  
4. **Move the card** to the next column when the exit gate is met (drag on board or update frontmatter + `python scripts/sync_kanban_folders.py`).  
5. Report: column at start, work done, column at end, blocker if any.

### Column pipeline (user intent → delivery)

```text
Triage → Spec → Plan → Todo → Scheduled → Ready → In Progress → Blocked → Review → Done
```

| Column | Purpose | Typical agent output |
|--------|---------|----------------------|
| **Triage** | Intake, scope, roadmap link | Card titled; track/labels set |
| **Spec** | Design before code | `specs/NNN-…-design.md` drafted → reviewed → **approved** |
| **Plan** | Executable tasks | `plans/NNN-…-prNN-….md` drafted → reviewed → **approved** |
| **Todo** | Dev priority breakdown | Numbered priorities on card / in plan |
| **Scheduled** | One queued slice for this run | Single item selected; branch named |
| **Ready** | Spec ↔ plan match; gates green | No `src/`/`web/` edits yet |
| **In Progress** | Implementation | Code on `feat/prNN-*` or `ai/job-*` |
| **Blocked** | Stop; document dependency | — |
| **Review** | Verify matrix, PR, fixes | Evidence attached |
| **Done** | Merged + recorded | `current_query` advanced; changelog |

**Hard rule:** No implementation in `src/` or `web/` until the card is **ready**, then **in-progress**. No plan without approved spec. No spec skipping for roadmap-sized work.

Non-roadmap tickets: still use a kanban card (create from **triage**); [BACKLOG.yml](docs/agent/BACKLOG.yml) is supplementary metadata.

---

## Agent runtime control

1. Read the active card under `.devtool/features/` and [KANBAN.yml](docs/agent/KANBAN.yml) + [current_query.md](docs/superpowers/roadmap/current_query.md) for roadmap PRs.  
2. For BACKLOG-only hotfixes: card at **ready** or **in-progress** with `files_allowed` documented on the card.  
3. Follow [RUNBOOK.md](docs/agent/RUNBOOK.md); stop on failed tests, blockers, missing approval, or rule conflicts.  
4. **One scheduled item per run** unless the user requests parallel work.

---

## Current PR (`current_query`)

Roadmap orientation (does not replace kanban column gates):

1. Read [KANBAN.yml](docs/agent/KANBAN.yml) `meta.current_pr` and the matching board card.  
2. Open the active roadmap narrative (today: [007 PR-48..57](docs/superpowers/roadmap/007-2026-06-03-pr48-pr57-post-beta-roadmap.md)).  
3. **`current_query`** = program pointer; **kanban `status`** = what the agent may do this run.  
4. On merge: card → **done**, then update `current_query.md`, then roadmap changelog.

Do not implement from roadmap rows alone; card must be **ready** / **in-progress** with approved spec + plan.

---

## Program loop (mapped to kanban)

Superpowers skills still apply; **kanban column determines which steps are allowed**.

| Kanban | Skills / actions | Output |
|--------|------------------|--------|
| **triage** | Scope check, roadmap link | Card + track labels |
| **spec** | `brainstorming`, `/grill-me` | Spec draft → review → **approved** |
| **plan** | `writing-plans`, plan↔spec review | Plan draft → **approved** |
| **todo** | Priority breakdown | Ordered task list on card/plan |
| **scheduled** | Pick one priority | This run’s scope + branch |
| **ready** | Gate check (spec, plan, acceptance) | Clear to code |
| **in-progress** | `executing-plans` / `subagent-driven-development` | Implementation |
| **review** | `requesting-code-review`, verification matrix | Fixes + green matrix |
| **done** | `finishing-a-development-branch`, update pointers | Merged; card closed |

**Branch rules:** Never commit to `main`/`master` without approval. Never claim tests passed without running them.

---

## Verification (default matrix)

```bash
python scripts/verify_phase_completion.py
cd web && npm run lint          # when web touched
cd web && npm run test:contracts
cd web && npm run test:e2e      # when UI/E2E affected
```

Targeted first: `pytest tests/path::test -v`  
Testing policy: [docs/agent-testing-policy.md](docs/agent-testing-policy.md) — no new test **files** without explicit approval.

---

## Runner contract (headless / queued)

1. Dedicated branch per job  
2. Agent = proposer; human or job flag = approver  
3. Smallest relevant verification; report commands + exit codes  
4. Structured result: files, summary, verification, risks, next action, **kanban column**  
5. **No commit** unless job allows; **no merge** to protected branches without approval  

---

## Where to look

| Need | Location |
|------|----------|
| Kanban gates | `.cursor/rules/20-kanban-workflow.mdc` |
| Board + columns | [docs/agent/KANBAN.md](docs/agent/KANBAN.md) · `.devtool/features/` |
| Active roadmap | `docs/superpowers/roadmap/` |
| Specs / plans | `docs/superpowers/specs/`, `plans/` |
| Architecture | `docs/current_architecture.md` |
| Release / smoke | `docs/release/` |
| Automation | `automation/`, `docs/agent-automation.md` |
| Agent runtime | `docs/agent/` (`RUNBOOK.md`, `BACKLOG.yml`) |

---

## Communication

Terse and technical. Start runs with **kanban column** + allowed phase; end with: **status**, **column change**, **changed paths**, **verification**, **blockers**, **next action**.
