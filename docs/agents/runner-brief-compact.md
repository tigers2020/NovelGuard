# Runner brief (compact)

Headless Linear jobs only. Full brief: `docs/agents/runner-brief.md`.

## Safety
- Repo only; one branch per job.
- No commit unless `commit: true` in prompt frontmatter.
- No merge to main without human approval.
- No destructive file moves without dry-run + approval.
- Smallest scoped verify; report command + exit code.
- New test **files** only when prompt says TEST_ALLOWED.

## Verify (default)
```bash
pytest <scoped> -v
python scripts/verify_phase_completion.py
cd web && npm run lint          # web touched
cd web && npm run test:contracts
```

## Output
Caveman mandatory for Linear reports and job stdout (see `.cursor/rules/caveman.mdc`).

## Job result
**status** · **changed paths** · **verification** · **blockers** · **next action**
