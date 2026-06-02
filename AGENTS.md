# AGENTS.md

Cross-agent entrypoint for **NovelGuard** — text novel duplicate detection and safe cleanup. [agents.md standard](https://agents.md/).

> **Canonical policy lives here.** Cursor detail: `.cursor/rules/`. Persona tone/cards: `persona/`. Architecture detail: `docs/current_architecture.md`.

---

## Communication

**Default mode: `/caveman`** — terse, technical, no filler. Articles, hedging, and pleasantries dropped; exact terms, errors, and code blocks unchanged. Resume only for security warnings, irreversible actions, or when fragment order risks misread. Off only when the user says `stop caveman` or `normal mode`.

---

## Project

NovelGuard scans text files, parses filenames, detects exact/near duplicates, groups them, previews via dry-run, and moves/deletes only after user approval.

**Workflow:** scan → filename parse → blocking → relation detect → (exact/near) → group → dry-run preview → user approval → move/cleanup

**Stack:** Python 3.12+ backend (`src/` layout); **UI:** React + TypeScript + Tailwind CSS v4 (`web/`, [DESIGN.md](DESIGN.md)). Versions: `pyproject.toml`, `web/package.json`.

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

Use the **Superpowers plugin** as the default process layer for **non-trivial** work. Invoke the matching skill when the situation applies (see `.cursor/rules/10-superpowers-routing.mdc`).

**Simple tasks — no Superpowers dependency:** Proceed directly when the request is small, localized, and low-risk. Skip `brainstorming`, `/grill-me`, spec/plan files, `executing-plans`, and branch-completion skills unless the user asks otherwise.

Typical simple tasks: typo or copy fix; one-file bug with clear cause; lint/format; config toggle; doc clarification; read-only Q&A; rename within one module.

Still required on simple tasks: `/caveman` (unless user opts out), **Hard invariants**, **Engineering standards**, **Testing** policy, and verification when claiming done.

Escalate to full Superpowers flow when any of: multi-file or cross-layer change; new behavior or API; architecture or safety impact; unclear root cause; user says “spec”, “plan”, or “full process”.

**Design baseline: `/grill-me`** (non-trivial spec/plan work only) — resolve spec and plan decisions interactively with the user: one question at a time, walk each branch of the design tree, recommend an answer per question. If the answer is in the codebase, explore the codebase instead of asking.


| Situation                                         | Skill                                                                                |
| ------------------------------------------------- | ------------------------------------------------------------------------------------ |
| New feature, behavior, or architecture change     | `brainstorming` → `/grill-me` for decisions → spec in `docs/superpowers/specs/`      |
| Approved design / spec exists                     | `writing-plans` → `/grill-me` for open decisions → plan in `docs/superpowers/plans/` |
| Plan ready; start implementation                  | `executing-plans` or `subagent-driven-development`                                   |
| Bug, regression, failing test, unclear cause      | `systematic-debugging`                                                               |
| Code change needing regression guard              | `test-driven-development` only where tests add **meaningful** coverage (see Testing) |
| Review requested                                  | `requesting-code-review`                                                             |
| Plan items implemented; branch ready to integrate | `finishing-a-development-branch` **then** `babysit` (PR merge-ready)                 |


**Planning gate (non-trivial work):** spec in `docs/superpowers/specs/` → human approval → plan in `docs/superpowers/plans/` → human approval → implement. Do not skip for multi-step work.

**Plan scope freeze:** When plan tasks A, B, C are done, **stop**. Do not add C-2, C-3, … or “while we’re here” work unless the user explicitly opens a new spec/plan cycle. New scope → new spec/plan → approval → implement.

**Branch completion (mandatory order):** after the approved plan is fully implemented and verification passes → user or agent declares the **PR slice closed** → **git commit** (see Security & commits) → `finishing-a-development-branch` (merge/PR/keep/discard) → if a PR exists or is created, `babysit` until merge-ready. Do not skip finishing; do not babysit before finishing.

If AGENTS and a Superpowers skill conflict on *how* to work, **user request and this file win** (see installed `using-superpowers` skill).

---

## Persona Dialogue

Every session uses the **personas required for the task** (not all roles every time). Work is **interactive with the user** — briefings surface choices; `/grill-me` handles unresolved design branches; implementation waits on spec/plan approval when gates apply.

Before code: `[시몬]` summarizes and assigns → assigned persona briefs in 1–2 sentences → then edit code. After code: `[테스]` tests (when warranted) → `[렉스]` verification pipeline.

Details: `.cursor/rules/20-persona-dialogue.mdc`, `persona/README.md`.

---

## Engineering standards

- **Standards-first:** Code and UI/UX follow widely recognized international standards (e.g. ISO/IEC norms where applicable, WCAG for accessibility, platform HIGs, PEP/style guides for Python, semantic HTML/CSS patterns where relevant).
- **Libraries before custom code:** Before implementing a feature, prefer the **standard library**, then **verified** third-party libraries, frameworks, and existing tools. Custom implementation only when reuse is unsuitable — document why in spec/plan when non-obvious.
- **Versions:** Pin and document dependencies in `pyproject.toml`; do not vendor or fork without approval.

## Hard invariants

- **Layers:** `domain` has no I/O/UI/DB/API; `application` does not import concrete infrastructure; `infrastructure` holds no business policy. See `docs/current_architecture.md`.
- **Safety:** no destructive file moves without dry-run preview and user approval.
- **Secrets:** API keys in `.env` only — never hardcode.
- **Evidence:** logs and reports are output/evidence, not inputs to duplicate-detection logic unless a spec says otherwise.
- **Honesty:** do not claim tests passed unless the exact command was run.

---

## Documentation map


| Purpose                          | Location                                                  |
| -------------------------------- | --------------------------------------------------------- |
| Design tokens & UX/UI guidelines | `DESIGN.md` (repo root)                                   |
| Design specs (new)               | `docs/superpowers/specs/###-YYYY-MM-DD-<topic>-design.md` |
| Implementation plans (new)       | `docs/superpowers/plans/###-YYYY-MM-DD-<topic>.md`        |
| Workflow index                   | `docs/superpowers/README.md`                              |
| Architecture & entry points      | `docs/current_architecture.md`, `docs/entry_points.md`    |
| Historical research/plans        | `documents/` (read-only for new work)                     |
| Session lessons                  | `documents/CURSOR_MEMO.md`                                |
| Refactoring history              | `docs/archive/`                                           |


---

## Testing

- **No indiscriminate test files** — do not add tests to “look busy” or mirror every private function. Extend existing `tests/` modules before creating new files.
- **Meaningful coverage only** — tests guard real behavior, regressions, or spec acceptance criteria.
- **New test files need explicit approval** — user must say `TEST_ALLOWED`, `create tests`, `add regression test`, or equivalent. Otherwise: run existing tests, change production code, propose minimal test plan and stop.
- **Forbidden without approval:** new `test_*.py` / `*_test.py` / `*.spec.`* / `*.test.*`, new `tests/` folders, weakened assertions, golden/snapshot churn, skip/xfail/delete to force pass, mock-only tests with no contract value.
- Reproduced production bugs → regression test (with approval) + `documents/CURSOR_MEMO.md` when appropriate.
- **Git guard:** `scripts/guard_new_tests.py` (pre-commit via `python scripts/install_git_hooks.py`) blocks staged new test files unless `ALLOW_NEW_TESTS=1`. Detail: `.cursor/rules/test-governance.mdc`.

---

## Verification

**One-shot (recommended):** `python scripts/verify_phase_completion.py` — `pytest` → `ruff check .` → `mypy src` → `black --check .` → `npm run lint` (requires Node/npm and `web/` deps installed)

**Run app:** `python src/main.py`

Detail: `.cursor/rules/40-testing-gates.mdc`

**Completion report must include:** changed files; exact commands; pass/fail counts; skipped tests if any; risks if verification was not run.

---

## Harness

- Prefer structure over prompts: lint, layer rules, approval gates, and **targeted** tests.
- Do not state unverified external facts as certain.

## Security & commits

- **PR closed → commit:** When one PR slice (plan scope) is **declared closed** — plan tasks done, verification passed, plan scope freeze acknowledged — create a **git commit** for that slice. Do not wait for a separate “please commit” unless the user defers closure.
- **Message format:** `[module] summary` — use plan/PR id when obvious (e.g. `[pr14c] quality analyzer and sqlite query rows`).
- **Before commit:** Run verification when the slice touched `src/`, `tests/`, or `web/` (`python scripts/verify_phase_completion.py` or the gate named in the plan). Do not claim done without evidence.
- **Staging:** Stage only files for the closed slice; exclude caches (`.mypy_cache`, `__pycache__`, `.ruff_cache`, `.pytest_cache`, `web/.vite`, etc.) and secrets (`.env`, credentials).
- **Push / PR:** Commit locally by default. Push or open a GitHub PR only when the user explicitly asks.
- **Empty tree:** If nothing to commit, report that — no empty commit.
- MCP usage: `.cursor/rules/55-mcp.mdc` (optional; CLI/docs often enough).

