# AGENTS.md

Cross-agent entrypoint for **NovelGuard**. Keep this file short and canonical.
Cursor activation lives in `.cursor/rules/`; deep workflow lives in `docs/superpowers/`.

---

## Project

NovelGuard is a local-first novel file scan, duplicate detection, review, and cleanup tool.

Core flow:

1. Scan files.
2. Parse filenames.
3. Detect exact and near duplicates.
4. Group candidates.
5. Preview changes with dry-run.
6. Apply moves or cleanup only after user approval.

Stack:

- Python 3.12+, `src/` layout.
- React + TypeScript UI under `web/`.
- Tailwind v4; design source is [DESIGN.md](DESIGN.md).
- Versions and dependencies live in `pyproject.toml` and `web/package.json`.

---

## Instruction Priority

On conflict, stop and report. Do not guess.

1. User request in the current session.
2. This `AGENTS.md`.
3. Applicable `.cursor/rules/*.mdc`.
4. Current `docs/`.
5. Historical `documents/`, read-only for new specs.
6. Opt-in skills and persona files.
7. General model knowledge.

---

## Task Scale

Small task:

- Make the smallest correct change.
- Do not create specs, plans, or new process docs.
- Do not invoke Superpowers or persona roleplay.
- Run the smallest useful verification, or say it was not run.

Large task:

- Use when work is multi-file, cross-layer, contract-changing, safety-sensitive, or unclear.
- Read the relevant spec or plan under `docs/superpowers/` before editing.
- Read [agent-workflow.md](docs/superpowers/agent-workflow.md) only when the task needs Superpowers routing or plan continuity.
- Use skills and persona files only when they add concrete value.

---

## Hard Rules

- Do not claim tests passed unless the exact command was run.
- Do not edit unrelated files.
- Do not hardcode secrets; use `.env`.
- Do not perform destructive file moves without dry-run preview and user approval.
- Logs and reports are output, not duplicate-detection inputs unless a spec says otherwise.
- Preserve existing public function/class signatures unless the user asks for a change.

---

## Architecture

See [docs/current_architecture.md](docs/current_architecture.md) for detail.

- `domain`: pure rules, value objects, policies. No I/O, UI, DB, or API.
- `application`: use cases, DTOs, and ports. No concrete infrastructure.
- `infrastructure`: filesystem, hashing, storage, external adapters. No business policy.
- `web`: React UI. Depends on API/DTO contracts, not infrastructure internals.
- `app`: composition and wiring.

---

## Agent phases (development missions)

Question policy: **only during Phase 1** (or before scope lock). After lock, no "continue?" between tasks.

| Phase | Name | Trigger |
| ----- | ---- | ------- |
| 0 | Intake | User states the development request |
| 1 | Grill-me / hardening | Attach `11-grill-me-hardening` from [00-core](.cursor/rules/00-core.mdc) index — once, no code |
| 2 | Lock | User: `Approved. Scope is locked.` (not bare `continue`) |
| 3 | Autonomous dev loop | Attach `21-autonomous-mission-execution` from index |
| 4 | Final gate | Lint / tests / build / e2e per locked plan |
| 5 | Merge / PR | Attach `90-branch-pr-finish` from index; stop on protection/CI/conflict |

Always-on: [00-core.mdc](.cursor/rules/00-core.mdc) (repo + mission + **only rules index**), [test-governance.mdc](.cursor/rules/test-governance.mdc).

Prompts: [docs/agent-operating-prompt.md](docs/agent-operating-prompt.md). Plan Mode can replace Phase 1.

---

## Development workflow (MCP)

On demand only. Attach `57` / `58` / `59` from [00-core.mdc](.cursor/rules/00-core.mdc) rules index. Tools: Context7, Supabase MCP, Playwright.

Skip with reason for docs-only edits or pure local refactors.

---

## Testing

- Extend existing tests first.
- New test files need explicit user approval.
- Guard: `scripts/guard_new_tests.py`.
- Full policy: [docs/agent-testing-policy.md](docs/agent-testing-policy.md).
- Always report exact commands run and pass/fail status.

---

## Verification

Recommended full gate:

```bash
python scripts/verify_phase_completion.py
```

Manual equivalents:

- `pytest`
- `ruff check .`
- `mypy src`
- `black --check .`
- `npm run lint`

Run app:

```bash
python src/main.py
```

---

## Where To Look

| Need | Location |
| ---- | -------- |
| Superpowers index | [docs/superpowers/README.md](docs/superpowers/README.md) |
| Workflow routing | [docs/superpowers/agent-workflow.md](docs/superpowers/agent-workflow.md) |
| UI tokens and UX | [DESIGN.md](DESIGN.md) |
| Architecture | [docs/current_architecture.md](docs/current_architecture.md) |
| Entry points | [docs/entry_points.md](docs/entry_points.md) |
| Testing policy | [docs/agent-testing-policy.md](docs/agent-testing-policy.md) |
| Cursor rules (index only) | [00-core.mdc](.cursor/rules/00-core.mdc) |
| Agent prompts | [docs/agent-operating-prompt.md](docs/agent-operating-prompt.md) |
| Persona cards | `persona/` |
| Historical docs | `documents/` |

---

## Communication

Default style is terse and technical. Keep answers focused on changed files, verification, skipped checks, and remaining risks.
