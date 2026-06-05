# Agent automation (Hermes + Cursor)

Reference for **queued / headless / cloud** runs. IDE sessions follow the same safety rules in [AGENTS.md](../AGENTS.md).

---

## Topology

```text
Telegram / Discord / GitHub / cron
        ↓
Hermes Gateway / Dispatcher  (single writer to queue)
        ↓
Task Queue (e.g. jobs/queue.sqlite)
        ↓
Cursor CLI | Cursor Automations | GitHub Actions
        ↓
branch → work → test/lint → diff summary → PR or patch
        ↓
Telegram (or configured notifier)
```

**Do not** let every bot invoke Cursor directly. One dispatcher enqueues; one worker per repo runs jobs sequentially.

---

## In-repo layout (NovelGuard)

```text
automation/
  config.example.yaml → config.yaml (local, gitignored)
  prompts/implement.md | review.md | test_fix.md
  schemas/job-payload.schema.json
  jobs/queue.sqlite
  logs/
  locks/NovelGuard.lock
  runners/job_worker.py | enqueue_job.py | queue.py | cursor_runner.py
```

Quick start: [automation/README.md](../automation/README.md).

### Linear webhook routing

**Routing is defined only in** `automation/linear/router.py`. Prompt YAML `trigger:` frontmatter is documentation; the router picks **one** prompt per webhook.

| Event | Prompt (`automation/prompts/linear/…`) |
| ----- | ------ |
| Issue create (Backlog) | `backlog/create-research.md` |
| Todo + `auto:research-done` | `todo/write-spec.md` |
| Backlog + `auto:spec-done` | `backlog/grill-plan.md` |
| Todo + `auto:grill-needs-revision` | `todo/revise-spec.md` |
| Todo + `auto:spec-done` (no plan) | `todo/defer-to-backlog.md` |
| Todo + `auto:plan-done` | `todo/write-todo-list.md` |
| status → In Progress | `in-progress/implement.md` |
| status → In Review | `in-review/verify.md` |

Routing logic: `automation/linear/router.py` (`resolve_planning_prompt`). Label-only updates route only when a **routing** label is present (`research-done`, `spec-done`, `plan-done`, `grill-needs-revision`); progress labels (`triaging`, `impl-running`, …) are ignored. Phase closeouts must use `save_issue` with status **and** done label in one call.

Hermes can enqueue the same JSON shape as [automation/examples/hermes-job.json](../automation/examples/hermes-job.json):

```bash
python scripts/hermes_enqueue.py automation/examples/hermes-job.json --id unique-id
cat job.json | python scripts/hermes_job_stdin.py
python scripts/automation_worker.py --once
```

Background worker (Windows): `automation/run-worker-loop.ps1`

## Optional external multi-repo hub

```text
cursor-automation/
  repos/NovelGuard/   # git clone
  repos/Serin/
  jobs/queue.sqlite   # shared dispatcher
```

Per-repo lock so only one job mutates a repo at a time.

---

## Bot roles (example)

| Bot | Role |
| --- | ---- |
| `cursor-dev` | Implementation jobs |
| `cursor-review` | Diff / PR review (read-only) |
| `cursor-ops` | Worker health, restart, logs |
| `cursor-research` | Docs / library lookup |

---

## Job lifecycle

1. Command ingested → `status = queued`
2. Worker: `git fetch`; checkout `main`; `git pull`
3. `git checkout -b ai/job-<id>`
4. Run Cursor CLI (`cursor-agent` / `agent` — confirm flags with `--help` on your install)
5. Verify: `ruff`, `mypy`, `pytest`, `npm run lint` as applicable
6. Emit: patch or diff stat, summary, test output, logs on failure
7. Notify channel; await human for commit/PR/merge if not pre-authorized

---

## Safety levels

| Level | Behavior |
| ----- | -------- |
| **1 — Safe** | Scheduled lint/test, log summary, PR review, inventory scans |
| **2 — Semi-auto** | Branch + implement + test + report; human approves commit/PR |
| **3 — Auto PR** | Through PR creation; human review before merge |
| **4 — Auto merge** | **Not recommended** for this repo |

---

## Prompt templates

### Implement (`prompts/implement.md`)

```text
You are working in this repository only.

Task:
{{TASK}}

Rules:
- Do not commit unless explicitly instructed.
- Do not modify unrelated files.
- Follow AGENTS.md and .cursor/rules.
- Run relevant tests.
- If tests fail, report exact command and cause.
- Return: changed files, summary, tests run, risks, next step.
```

### Review (`prompts/review.md`)

```text
Review the current git diff. Do not modify files.

Focus: correctness, regression, layer violations, missing tests,
unsafe file ops, scope creep.

Return blocking issues first, then suggestions.
```

---

## Windows execution

| Option | Notes |
| ------ | ----- |
| **WSL2 + systemd** | Preferred for long-running worker |
| **Task Scheduler** | `python ...\job_worker.py` on interval or at logon |
| **Docker** | Strong isolation; CLI auth and bind mounts need setup |

---

## NovelGuard verification (copy into worker)

```bash
ruff check .
mypy src
pytest                    # or targeted ::test
python scripts/verify_phase_completion.py   # full gate
cd web && npm run lint    # if web touched
```

---

## Checklist

- [ ] CLI installed; `cursor-agent --help` / `agent --help` documented for your version
- [ ] Queue + per-repo lock
- [ ] Worker: one job at a time per repo
- [ ] Every job uses a new branch; no direct `main` writes
- [ ] Failure logs retained
- [ ] Destructive ops require approval token in job payload
- [ ] Optional: migrate stable jobs to Cursor Automations / GitHub Actions

---

## Links

- [Cursor CLI](https://cursor.com/cli)
- [Cursor Automations](https://cursor.com/blog/automations)
