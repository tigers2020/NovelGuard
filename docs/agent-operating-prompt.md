# Agent operating prompts (NovelGuard)

Copy-paste for **IDE**, **Telegram/Hermes jobs**, or **Cursor CLI** runners.

Rules index: **`@.cursor/rules/00-automation-core.mdc`** (only place that lists rule paths).

Deep automation layout: [agent-automation.md](agent-automation.md).

---

## Queued / headless job (default)

```text
@AGENTS.md @.cursor/rules/00-automation-core.mdc @.cursor/rules/10-runner-safety.mdc

Repository only. Task:
{{TASK}}

Rules:
- Work on branch ai/job-{{ID}} (create if missing). Do not touch main.
- Do not commit unless this message says commit: true.
- Smallest verification first; report every command and exit code.
- Return: changed files, summary, tests run, risks, next step.
```

---

## Implementation (interactive)

```text
@AGENTS.md @.cursor/rules/00-automation-core.mdc

Task: <one clear scope>

- Minimal diff; no unrelated files
- Run: <pytest path::test | ruff | etc.>
- Do not commit unless I ask
```

---

## Review only (no edits)

```text
@AGENTS.md @.cursor/rules/10-runner-safety.mdc

Review current git diff. Do not modify files.

Blocking issues first, then suggestions.
Focus: correctness, layers, tests, unsafe file ops, scope creep.
```

---

## PR finish

```text
@AGENTS.md @.cursor/rules/90-pr-finish.mdc @.cursor/rules/30-verify-gates.mdc

Prepare PR for current branch. Run full gate if not yet run.
List exact verification commands in test plan.
```

---

## Web / UI

```text
@AGENTS.md @.cursor/rules/40-web-tailwind.mdc

<scope>
```

Optional browser check: `@.cursor/rules/53-mcp-playwright.mdc`

---

## Library docs uncertain

```text
@AGENTS.md @.cursor/rules/51-mcp-context7.mdc

<scope>
```

---

## Multi-step batch (no phase ceremony)

```text
@AGENTS.md @.cursor/rules/00-automation-core.mdc

Scope: <paste>

Tasks 1–N: <list>

Execute in order without asking between steps.
Stop only on true blockers (10-runner-safety).
One line per completed task; final summary at end.
```

---

## Legacy Superpowers / grill-me

Optional for large design work only — not default. See [superpowers/agent-workflow.md](superpowers/agent-workflow.md).
