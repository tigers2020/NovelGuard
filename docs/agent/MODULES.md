# Module boundaries (agent)

Thin index — full detail lives in code and architecture docs.

| Area | Path | Agent may edit when |
|------|------|---------------------|
| Domain | `src/domain/` | Ticket allows; no UI/bridge shortcuts |
| Application | `src/application/` | Ticket allows |
| Infrastructure | `src/infrastructure/` | Ticket allows |
| Web UI | `web/` | Ticket allows; run web lint/tests if touched |
| App / bridge | `src/app/` | Ticket allows; bridge contract tests if API touched |
| Superpowers specs/plans | `docs/superpowers/specs/`, `plans/` | Roadmap PR workflow only — not via `BACKLOG.yml` unless ticket explicitly allows |
| Agent runtime | `docs/agent/` | Docs tickets with `files_allowed` |

**Default forbidden** unless ticket lists paths: unrelated modules, `persona/`, legacy `protocols/` (opt-in per AGENTS.md).
