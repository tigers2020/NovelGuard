# Solution index (agent)

Rule → where to implement. Expand rows when adding agent tickets; link specs/plans for PR work.

| Rule / constraint | Implement via | Verify |
|-------------------|---------------|--------|
| No destructive moves without preview + approval | `app/` preview/apply guards, bridge API | bridge contract tests, E2E apply flows |
| Layering: domain → application → infrastructure → web → app | Respect module boundaries in [MODULES.md](./MODULES.md) | import lint / architecture tests if present |
| Roadmap PR requires approved spec + plan | Superpowers `specs/`, `plans/` | Do not code from roadmap row alone |
| One ticket per agent run | [RUNBOOK.md](./RUNBOOK.md) | `AGENT_STATE.json`, run output |
| Release notes vs agent log | root `CHANGELOG.md` vs [CHANGELOG-agent.md](./CHANGELOG-agent.md) | Keep separate |

For a selected `BACKLOG.yml` ticket, read only the rows and docs tied to `module` and `files_allowed`.
