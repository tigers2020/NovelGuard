# AGENTS.md

Canonical repo guide for humans, Cursor, Codex, CLI runners, and automations.

## Project

NovelGuard — local-first novel scan, duplicate detection, review, cleanup.

Stack: Python 3.12+ (`src/`), React+TS (`web/`), Tailwind v4 ([DESIGN.md](DESIGN.md)).  
Layers: `domain` → `application` → `infrastructure` → `web` → `app` ([docs/current_architecture.md](docs/current_architecture.md)).

**Safety:** no destructive file moves without dry-run preview + user approval.

---

## Contract

Stop and report on instruction conflict.

1. Explicit user / job message  
2. This file  
3. Matching `.cursor/rules/*.mdc`
4. Named spec under `docs/superpowers/specs/`
5. Referenced docs
6. General model knowledge

- Minimal diff; no unrelated files.
- Preserve public function/class signatures unless asked.
- No commit, push, PR, merge, or publish without explicit approval.
- Opt-in only: `persona/`, legacy `protocols/`, Superpowers ceremony.

## Git branch policy

**No branch creation without a special reason.** Default: stay on the current branch; do not open a new branch “to be safe” or “for cleanup.”

Agents **must not** create, rename, switch, delete, merge, or rebase branches unless the user explicitly requested that exact operation.

Forbidden for agents (also enforced by `scripts/git_guard.py` on automation PATH):

- `git checkout -b`, `git switch -c`, `git branch <name>`, `git branch -D`
- `git merge`, `git rebase`, `git reset --hard`, `git worktree add`
- `git checkout <branch>`, `git switch <branch>` (branch switches)

Work only on the **current** branch. If a branch operation seems necessary, stop and report the exact command — do not run it.

Orchestrator (`prepare_branch`) may create job branches; agents may still `git status`, `git diff`, `git add`, `git commit` when the job allows.

Details: [docs/agents/git-safety.md](docs/agents/git-safety.md).

---

## Routing

| Need | Load |
|------|------|
| Automation / queue | [docs/agent-automation.md](docs/agent-automation.md), [docs/agents/runner-brief.md](docs/agents/runner-brief.md) |
| Roadmap PR loop | [docs/agents/program-loop.md](docs/agents/program-loop.md) |
| Large spec / plan | [docs/superpowers/agent-workflow.md](docs/superpowers/agent-workflow.md) |
| Testing policy | [docs/agent-testing-policy.md](docs/agent-testing-policy.md) |
| UI system | [DESIGN.md](DESIGN.md) |

---

## `current_query` (roadmap PRs)

1. Active roadmap: [docs/superpowers/roadmap/README.md](docs/superpowers/roadmap/README.md)  
2. First non-**Done** row in phase table.  
3. Require approved spec + plan before implement — see [program-loop.md](docs/agents/program-loop.md).

---

## Verification

```bash
python scripts/verify_phase_completion.py
cd web && npm run lint          # web touched
cd web && npm run test:contracts
cd web && npm run test:e2e      # UI/E2E affected
```

Targeted: `pytest tests/path::test -v`  
Never claim tests passed unless the command was run and exited 0.

---

## Communication

**Caveman mandatory** (`.cursor/rules/caveman.mdc`) — terse, no fluff; tech terms exact. Off only if user says `stop caveman` / `normal mode`.

Automated jobs end with: **status**, **changed paths**, **verification**, **blockers**, **next action**.
