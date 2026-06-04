# AGENTS.md

Canonical entry for **humans, Cursor IDE, Cursor CLI runners, and Cloud Automations** on NovelGuard.

**Deep automation:** [docs/agent-automation.md](docs/agent-automation.md)  
**Superpowers workflow (large work):** [docs/superpowers/agent-workflow.md](docs/superpowers/agent-workflow.md)

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
3. Task spec under `docs/superpowers/specs/` (when named)  
4. General model knowledge  

Opt-in unless requested: `persona/`, legacy `protocols/`, Superpowers ceremony.

---

## Current PR (`current_query`)

Resolve the active PR slice before spec/plan/implementation:

1. Read [docs/superpowers/roadmap/README.md](docs/superpowers/roadmap/README.md) for the **active** roadmap file.  
2. Open that roadmap (today: [007 PR-48..57](docs/superpowers/roadmap/007-2026-06-03-pr48-pr57-post-beta-roadmap.md)).  
3. **`current_query`** = first PR row in the phase table whose status is not **Done** (top-to-bottom program order).  
4. Optional tracker: [docs/superpowers/roadmap/current_query.md](docs/superpowers/roadmap/current_query.md) — update when a PR merges.

Do not implement from roadmap rows alone; require an **approved spec** and **approved plan** per PR.

---

## Program loop (PR-48..57 and future tracks)

Run steps **1 → 15** for each `current_query` until the active roadmap has no remaining PRs.

| Step | Skill / action | Output |
|------|----------------|--------|
| 1 | Read roadmap | `current_query` PR id + links |
| 2 | `brainstorming` | PR intent, constraints, success criteria |
| 3 | `brainstorming` | Spec draft → `docs/superpowers/specs/NNN-…-design.md` |
| 4 | `/grill-me` (self) | Lock decisions in spec; no user Q&A unless blocked |
| 5 | `brainstorming` | Spec self-review; status **approved** |
| 6 | `writing-plans` | Plan → `docs/superpowers/plans/NNN-…-prNN-….md` |
| 7 | Plan vs spec review | Fix gaps before code |
| 8 | `subagent-driven-development` or `executing-plans` | Implement on `feat/prNN-*` or `ai/job-*` branch |
| 9 | `requesting-code-review` | Spec compliance review (subagent) |
| 10 | `receiving-code-review` | Triage feedback; verify before fixing |
| 11 | Fix review findings | Minimal diffs + re-review |
| 12 | `/try-and-error-fix` | Full matrix green (evidence required) |
| 13 | `finishing-a-development-branch` + `/babysit` | PR open; CI/comments until merge-ready |
| 14 | Read roadmap | Confirm PR **Done**; advance `current_query` |
| 15 | Repeat | Until active roadmap phase table is complete |

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
4. Structured result: files, summary, verification, risks, next step  
5. **No commit** unless job allows; **no merge** to protected branches without approval  

---

## Where to look

| Need | Location |
|------|----------|
| Active roadmap | `docs/superpowers/roadmap/` |
| Specs / plans | `docs/superpowers/specs/`, `plans/` |
| Architecture | `docs/current_architecture.md` |
| Release / smoke | `docs/release/` |
| Automation | `automation/`, `docs/agent-automation.md` |

---

## Communication

Terse and technical. End automated jobs with: **status**, **changed paths**, **verification**, **blockers**, **next action**.
