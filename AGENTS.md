# AGENTS.md

Canonical repo guide for humans, Cursor, Codex, CLI runners, and automations.

## Project

NovelGuard — local-first novel scan, duplicate detection, review, cleanup.

Stack: Python 3.12+ (`src/`), React+TS (`web/`), Tailwind v4 ([DESIGN.md](DESIGN.md)).  
Layers: `domain` → `application` → `infrastructure` → `web` → `app`.  
IA / UX contract: [docs/architecture/main-ux-contract.md](docs/architecture/main-ux-contract.md).  
Entry points & verification: [docs/entry_points.md](docs/entry_points.md).

**Safety:** no destructive file moves without dry-run preview + user approval. Partial-success recovery / undo contract: [docs/superpowers/specs/2026-06-06-partial-recovery-undo-design.md](docs/superpowers/specs/2026-06-06-partial-recovery-undo-design.md) (design; not yet implemented).

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
| UX / IA (locked) | [docs/architecture/main-ux-contract.md](docs/architecture/main-ux-contract.md) |
| Run & verify commands | [docs/entry_points.md](docs/entry_points.md) |

---

## `current_query` (roadmap PRs)

1. Active roadmap: [docs/superpowers/roadmap/README.md](docs/superpowers/roadmap/README.md)  
2. First non-**Done** row in phase table.  
3. Require approved spec + plan before implement — see [program-loop.md](docs/agents/program-loop.md).

---

## Verification

```bash
python scripts/verify_phase_completion.py
python -m pytest -m large_library  # opt-in ~7.2k SLO gate (after generate_large_library_fixture.py)
npm run lint --prefix web       # web touched
npm run test:contracts --prefix web
npm run build --prefix web      # web touched (production gate)
npm run test:e2e --prefix web   # UI/E2E affected
pytest tests/test_bridge_contract.py -v   # Python bridge parity
```

Targeted: `pytest tests/path::test -v`  
Never claim tests passed unless the command was run and exited 0.

---

## Communication

**Caveman mandatory** (`.cursor/rules/caveman.mdc`) — terse, no fluff; tech terms exact. Off only if user says `stop caveman` / `normal mode`.

Automated jobs end with: **status**, **changed paths**, **verification**, **blockers**, **next action**.
