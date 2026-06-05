# Agent operating prompts (NovelGuard)

Copy-paste for **IDE**, **Telegram/Hermes jobs**, or **Cursor CLI** runners.

**Context slimming:** headless jobs use `@docs/agents/runner-brief.md` only — not full AGENTS.md + multiple rules. IDE loads [AGENTS.md](../AGENTS.md) + conditional `.cursor/rules/`.

**Output:** caveman mandatory (`.cursor/rules/caveman.mdc`). Off only on `stop caveman` / `normal mode`.

Deep automation: [agent-automation.md](agent-automation.md).

---

## Queued / headless job (default)

```text
@docs/agents/runner-brief.md

Repository only. Task:
{{TASK}}

- Branch ai/job-{{ID}} (create if missing). Do not touch main.
- No commit unless commit: true.
- Smallest verification; report command + exit code.
- Return: changed files, summary, tests, risks, next step.
```

---

## Implementation (interactive)

```text
Task: <one clear scope>

- Minimal diff
- Run: <pytest path::test | ruff | etc.>
- Do not commit unless I ask
```

(AGENTS.md + rules load automatically in IDE.)

---

## Review only (no edits)

```text
Review current git diff. Do not modify files.

Blocking issues first, then suggestions.
Focus: correctness, layers, tests, unsafe file ops, scope creep.
```

---

## PR finish

```text
@.cursor/rules/90-pr-finish.mdc @.cursor/rules/30-verify-gates.mdc

Prepare PR for current branch. Run full gate if not yet run.
List exact verification commands in test plan.
```

---

## Web / UI

```text
@.cursor/rules/40-web-tailwind.mdc

<scope>
```

---

## Library docs uncertain

Use Context7 MCP when API details are unclear — do not paste full docs into prompt.

---

## Multi-step batch

```text
Scope: <paste>

Tasks 1–N: <list>

Execute in order. Stop only on true blockers.
One line per task; final summary at end.
```

---

## Legacy Superpowers / grill-me

Optional for large design work only. See [superpowers/agent-workflow.md](superpowers/agent-workflow.md).
