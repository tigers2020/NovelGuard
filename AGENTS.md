# AGENTS.md

Canonical entry for **humans, Cursor IDE, Cursor CLI runners, and Cloud Automations** working on NovelGuard.

Activation: `.cursor/rules/` (automation-first). Deep runner/Hermes design: [docs/agent-automation.md](docs/agent-automation.md).

---

## Project

NovelGuard — local-first novel scan, duplicate detection, review, and cleanup.

Flow: scan → parse filenames → exact/near duplicate detection → group → dry-run preview → apply only after approval.

Stack: Python 3.12+ (`src/`), React+TS (`web/`), Tailwind v4 ([DESIGN.md](DESIGN.md)). Versions in `pyproject.toml`, `web/package.json`.

Layers ([docs/current_architecture.md](docs/current_architecture.md)): `domain` → `application` → `infrastructure` → `web` → `app`. No layer violations.

---

## Automation stack (how work arrives)

```text
Telegram / Discord / GitHub / cron / webhook
        ↓
Hermes gateway + dispatcher (single queue writer)
        ↓
job queue (e.g. queue.sqlite) + per-repo lock
        ↓
Cursor CLI runner | Cursor Automations | IDE session
        ↓
branch → edit → verify → diff summary → PR or patch
        ↓
notifier (e.g. Telegram)
```

**Prefer when stable:** Cursor Automations / Cloud Agent (schedule, PR, issue, webhook).

**Default for Hermes:** one local **Cursor CLI runner** per repo, sequential jobs, branch isolation.

**IDE chat:** same rules; user is the approver.

---

## Instruction priority

On conflict, stop and report. Do not guess.

1. Explicit job payload / user message for this run.
2. This `AGENTS.md`.
3. Applicable `.cursor/rules/*.mdc` (see [00-automation-core.mdc](.cursor/rules/00-automation-core.mdc) index).
4. Task-local spec under `docs/` (if the job names one).
5. General model knowledge.

Opt-in only unless the job requests it: `persona/`, Superpowers skills, long workflow docs.

---

## Runner contract (CLI / cloud / queued jobs)

Every automated job MUST:

1. Work on a **dedicated branch** (`ai/job-<id>` or job naming convention). Never commit directly to `main`/`master`.
2. Treat the agent as **proposer**; human (or explicit job flag) is **approver**.
3. Run the **smallest relevant verification**; report exact commands and pass/fail. Never claim tests passed without running them.
4. Return a structured result:
   - changed files
   - implementation summary
   - tests/commands run
   - risks
   - recommended next step
5. **Do not commit** unless the job explicitly allows it; **never merge** to protected branches without approval.

Allowed without extra approval (unless repo policy says otherwise): branch create, edit, test, commit, open PR.

Requires explicit approval: push to `main`, merge, destructive migrations, mass delete, secrets changes, major dependency bumps.

NovelGuard-specific: no destructive file moves without dry-run + approval; logs/reports are not duplicate-detection inputs unless a spec says so.

---

## Task scale

| Scale | When | Do |
| ----- | ---- | -- |
| **Small** | Single area, obvious fix | Minimal diff; skip new specs/plans; smallest verification |
| **Large** | Multi-file, contract, safety, unclear | Read named spec/plan under `docs/` first; full gate at end |

No grill-me phases, scope-lock phrases, or persona roleplay by default.

---

## Verification

Smallest useful check first, then widen if needed.

```bash
# Python (typical)
ruff check .
mypy src
pytest path::test          # prefer targeted
python scripts/verify_phase_completion.py   # 9/9 full gate (fixture smoke; exe launch if dist/ built)
python scripts/beta_gate.py               # packaging + fixture + launch smokes only

# Web (when touched)
cd web && npm run lint
```

Run app: `python src/main.py`

Testing policy: [docs/agent-testing-policy.md](docs/agent-testing-policy.md). New test **files** need explicit approval (`scripts/guard_new_tests.py`).

---

## Rules index

Attach with `@` from the table in [00-automation-core.mdc](.cursor/rules/00-automation-core.mdc).

Always-on: `00-automation-core`, `10-runner-safety`, `20-novelguard-project`, `30-verify-gates`.

---

## Where to look

| Need | Location |
| ---- | -------- |
| Automation / Hermes / runner | [automation/README.md](automation/README.md), [docs/agent-automation.md](docs/agent-automation.md) |
| Architecture | [docs/current_architecture.md](docs/current_architecture.md) |
| Entry points | [docs/entry_points.md](docs/entry_points.md) |
| UI / tokens | [DESIGN.md](DESIGN.md) |
| Testing | [docs/agent-testing-policy.md](docs/agent-testing-policy.md) |
| Historical docs | `documents/` (read-only for new specs) |

---

## Communication

Terse and technical. For runner jobs, end with: status, changed paths, verification, blockers, next action.
