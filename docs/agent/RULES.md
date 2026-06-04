# Rules checklist (agent)

Digest at run start — do **not** paste this file in full. Mark each line: **applied** | **N/A** | **conflict**.

| ID | Rule | Source |
|----|------|--------|
| R-001 | Instruction priority: user → AGENTS.md → named spec → model | AGENTS.md |
| R-002 | Roadmap PR: approved spec + plan before implementation | AGENTS.md, RUNBOOK.md |
| R-003 | One ticket per run; stop on test/lint/type failure | RUNBOOK.md |
| R-004 | No destructive file ops without dry-run preview + user approval | AGENTS.md |
| R-005 | No new test **files** without explicit approval | docs/agent-testing-policy.md |
| R-006 | Do not claim tests passed without running them | AGENTS.md |
| R-007 | No commit/merge to protected branches without approval | AGENTS.md |
| R-008 | Edit only `files_allowed`; respect `files_forbidden` on backlog tickets | BACKLOG.yml |
| R-009 | Agent changelog ≠ release changelog | CHANGELOG-agent.md vs root CHANGELOG.md |

On **conflict**, stop and report before editing.
