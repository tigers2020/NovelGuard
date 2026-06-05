@AGENTS.md @.cursor/rules/00-automation-core.mdc @.cursor/rules/10-runner-safety.mdc

# Linear issue trigger — NovelGuard

You were triggered because a Linear issue was **created** (or assigned to you).

## Issue context (fill from Linear MCP before any code)

- Identifier: {{ISSUE_IDENTIFIER}}
- URL: {{ISSUE_URL}}
- Project: NovelGuard
- Branch: ai/linear-{{ISSUE_IDENTIFIER}}

**First action:** Use Linear MCP `get_issue` for `{{ISSUE_IDENTIFIER}}`.
Read title, description, labels, priority, project, relations, and git branch name if present.
If project is not **NovelGuard**, stop and report `OUT_OF_SCOPE`.

## Required reads (repo, in order)

1. `AGENTS.md`
2. `docs/current_architecture.md` — if touching layers / file ops
3. `docs/agent/RUNBOOK.md` — if issue maps to backlog/kanban ticket
4. Named spec/plan only if issue body links one:
   - `docs/superpowers/specs/<file>`
   - `docs/superpowers/plans/<file>`
   - `.devtool/features/<work-id>-*.md`

Do **not** invent scope beyond the issue + linked docs.

## Triage (do this before editing)

Classify the issue:

| Type | Signal | Agent action |
|------|--------|----------------|
| **bug** | repro steps, regression, error | reproduce → minimal fix → targeted test |
| **feature** | new behavior, acceptance criteria | check for approved spec/plan; if missing, draft triage comment only — **no product code** unless spec linked |
| **chore** | lint, refactor, docs, tooling | smallest diff in named paths only |
| **blocked** | missing approval, destructive file ops, unclear AC | Linear comment + status **Blocked**; stop |

**Safety (NovelGuard):** No destructive file moves without dry-run preview + explicit user approval in the issue or job payload.

## Git / branch

1. `git fetch`
2. Checkout or create `ai/linear-{{ISSUE_IDENTIFIER}}` from latest default branch
3. Do **not** commit to `main`/`master`
4. Do **not** commit unless job says `commit: true`

## Linear status workflow

1. After triage starts → `save_issue` state **In Progress** (if not already)
2. If blocked → state **Blocked** + `save_comment` with reason
3. On completion → `save_comment` with summary + verification commands
4. If work merged / verified → state **Done** (only when evidence exists)

## Implementation rules

- Minimal diff; no unrelated files
- Layers: `domain` → `application` → `infrastructure` → `web` → `app`
- Allowed paths unless issue says otherwise: `src/`, `web/src/`, `tests/`, `docs/agent/`, linked `.devtool/features/`
- No new test **files** without explicit approval (see `docs/agent-testing-policy.md`)
- Do not claim tests passed without running them

## Verification (smallest relevant first)

```bash
pytest tests/path::test_name -v
ruff check <paths>
mypy src
cd web && npm run lint
python scripts/verify_phase_completion.py
```

Stop on first failure; report exact command + exit code + stderr tail.

## Return format (mandatory)

### Status
`DONE` | `BLOCKED` | `NEEDS_SPEC` | `NEEDS_APPROVAL`

### Issue
{{ISSUE_IDENTIFIER}} — one-line restatement of acceptance criteria

### Changed paths
- list every file touched (or `none`)

### Verification
- command → exit code → pass/fail

### Linear updates
- state changed? (yes/no + to what)
- comment posted? (yes/no + summary)

### Risks
- bullet list

### Next action
- one concrete step for human or next automation run
