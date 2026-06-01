# AGENTS.md

Cross-agent entrypoint for **NovelGuard** — text novel duplicate detection and safe cleanup. [agents.md standard](https://agents.md/).

> **Canonical policy lives here.** Cursor detail: `.cursor/rules/`. Persona tone/cards: `persona/`. Architecture detail: `docs/current_architecture.md`.

---

## Project

NovelGuard scans text files, parses filenames, detects exact/near duplicates, groups them, previews via dry-run, and moves/deletes only after user approval.

**Workflow:** scan → filename parse → blocking → relation detect → (exact/near) → group → dry-run preview → user approval → move/cleanup

**Stack:** Python 3.12+, `src/` layout, PySide6 GUI. Versions and deps: `pyproject.toml`.

---

## Instruction priority

When instructions conflict, stop and report — do not guess.

1. User's explicit request in the current session
2. This `AGENTS.md`
3. Applicable `.cursor/rules/*.mdc` (glob-matched)
4. `docs/` and `documents/` (historical)
5. Installed Superpowers skills (per routing table below)
6. General model knowledge

---

## Superpowers workflow

Use Superpowers as the default process layer. Invoke the skill when the situation matches (see `.cursor/rules/10-superpowers-routing.mdc`).

| Situation | Skill |
|-----------|--------|
| New feature, behavior, or architecture change | `brainstorming` first |
| Approved design / spec exists | `writing-plans` |
| Plan ready; start implementation | `executing-plans` or `subagent-driven-development` |
| Bug, regression, failing test, unclear cause | `systematic-debugging` |
| Code change (where practical) | `test-driven-development` |
| Review requested | `requesting-code-review` |
| Work complete | `finishing-a-development-branch` |

**Planning gate (non-trivial work):** spec in `docs/superpowers/specs/` → human approval → plan in `docs/superpowers/plans/` → human approval → implement. Do not skip for multi-step work.

If AGENTS and a Superpowers skill conflict on *how* to work, **user request and this file win** (see installed `using-superpowers` skill).

---

## Persona Dialogue

Before code: `[시몬]` summarizes and assigns → assigned persona briefs in 1–2 sentences → then edit code. After code: `[테스]` tests → `[렉스]` verification pipeline.

Details: `.cursor/rules/20-persona-dialogue.mdc`, `persona/README.md`.

---

## Hard invariants

- **Layers:** `domain` has no I/O/UI/DB/API; `application` does not import concrete infrastructure; `infrastructure` holds no business policy. See `docs/current_architecture.md`.
- **Safety:** no destructive file moves without dry-run preview and user approval.
- **Secrets:** API keys in `.env` only — never hardcode.
- **Evidence:** logs and reports are output/evidence, not inputs to duplicate-detection logic unless a spec says otherwise.
- **Honesty:** do not claim tests passed unless the exact command was run.

---

## Documentation map

| Purpose | Location |
|---------|----------|
| Design specs (new) | `docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md` |
| Implementation plans (new) | `docs/superpowers/plans/YYYY-MM-DD-<topic>.md` |
| Workflow index | `docs/superpowers/README.md` |
| Architecture & entry points | `docs/current_architecture.md`, `docs/entry_points.md` |
| Historical research/plans | `documents/` (read-only for new work) |
| Session lessons | `documents/CURSOR_MEMO.md` |
| Refactoring history | `docs/archive/` |

---

## Verification

**One-shot (recommended):** `python scripts/verify_phase_completion.py` — `pytest` → `ruff check .` → `mypy src` → `black --check .`

**Run app:** `python src/main.py`

Detail: `.cursor/rules/40-testing-gates.mdc`

**Completion report must include:** changed files; exact commands; pass/fail counts; skipped tests if any; risks if verification was not run.

---

## Harness

- Prefer structure over prompts: tests, lint, layer rules, approval gates.
- Reproduced mistakes → tests + `documents/CURSOR_MEMO.md`.
- Do not state unverified external facts as certain.

## Security & commits

- Commits: `[module] summary` after verification when the user asks for a commit.
- MCP usage: `.cursor/rules/55-mcp.mdc` (optional; CLI/docs often enough).
