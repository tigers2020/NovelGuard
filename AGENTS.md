# AGENTS.md

Router for humans, Cursor IDE, CLI runners, and automations.

| Need | Doc |
|------|-----|
| Automation / queue | [docs/agent-automation.md](docs/agent-automation.md) |
| Headless job brief | [docs/agents/runner-brief.md](docs/agents/runner-brief.md) |
| PR program loop (steps 1–15) | [docs/agents/program-loop.md](docs/agents/program-loop.md) |
| Large work / Superpowers | [docs/superpowers/agent-workflow.md](docs/superpowers/agent-workflow.md) |

---

## Project

NovelGuard — local-first novel scan, duplicate detection, review, cleanup.

Stack: Python 3.12+ (`src/`), React+TS (`web/`), Tailwind v4 ([DESIGN.md](DESIGN.md)).  
Layers: `domain` → `application` → `infrastructure` → `web` → `app` ([docs/current_architecture.md](docs/current_architecture.md)).

**Safety:** No destructive file moves without dry-run preview + user approval.

---

## Instruction priority

On conflict, stop and report.

1. Explicit user / job message  
2. This file  
3. Named spec under `docs/superpowers/specs/`  
4. General model knowledge  

Opt-in unless requested: `persona/`, legacy `protocols/`, Superpowers ceremony.

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
Policy: [docs/agent-testing-policy.md](docs/agent-testing-policy.md)

---

## Communication

**Caveman mandatory** (`.cursor/rules/caveman.mdc`) — terse, no fluff; tech terms exact. Off only if user says `stop caveman` / `normal mode`.

Automated jobs end with: **status**, **changed paths**, **verification**, **blockers**, **next action**.
