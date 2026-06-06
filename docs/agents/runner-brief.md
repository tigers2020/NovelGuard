# Runner brief (headless / Linear automation)

Minimal context for queued jobs. IDE sessions use [AGENTS.md](../../AGENTS.md) + conditional `.cursor/rules/`.

## Safety

- Repo only; dedicated branch per job (orchestrator creates via `prepare_branch`).
- **Agents must not** create, switch, merge, rebase, or hard-reset branches — enforced by `git_guard` on agent PATH; job fails if branch changes during cursor run.
- **No commit** unless job frontmatter / payload says `commit: true`.
- **No merge** to `main`/`master` without human approval.
- No destructive file moves without dry-run note + approval.
- Logs/reports ≠ duplicate-detection inputs unless spec says so.
- Smallest relevant verification; report command + exit code.
- New test **files** only when prompt says TEST_ALLOWED or user approves.

## Layers

`domain` → `application` → `infrastructure` → `web` → `app` ([main-ux-contract.md](../architecture/main-ux-contract.md)).

## Verify (default)

```bash
pytest <scoped> -v
python scripts/verify_phase_completion.py
cd web && npm run lint          # web touched
cd web && npm run test:contracts
cd web && npm run test:e2e      # UI/E2E affected
```

## Output style (mandatory)

**Caveman** — terse, no fluff. Tech terms exact. See `.cursor/rules/caveman.mdc`.

| Output | Rule |
|--------|------|
| Linear `## … report` / blocked / rebuke | lead with **Summary (caveman)** — 3–8 short lines |
| Job stdout to worker | caveman |
| Spec / Plan body | clear prose OK; section summaries caveman |

Exceptions: security, irreversible ops, clarity-risk sequences.

## Job result format

**status** · **changed paths** · **verification** · **blockers** · **next action** (caveman)

Automation layout: [agent-automation.md](../agent-automation.md).
