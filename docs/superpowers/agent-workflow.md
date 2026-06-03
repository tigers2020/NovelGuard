# Agent Workflow

Deep context for non-trivial NovelGuard work. This file is not default context.
Read it only when the task needs spec/plan gates, Superpowers skills, or naming rules.

Canonical short guide: [AGENTS.md](../../AGENTS.md).
Automation / runners: [docs/agent-automation.md](../agent-automation.md).
Activation: `.cursor/rules/00-automation-core.mdc`.

---

## When To Use This Doc

| Task scale | Action |
| ---------- | ------ |
| Small / localized | Skip this file. Implement directly. |
| Large / PR slice / architecture | Read the relevant spec/plan first, then sections below as needed. |

---

## Superpowers Skill Routing

Invoke skills only when the task benefits, not on every turn.

| Situation | Skill |
| --------- | ----- |
| New feature, behavior, or architecture change | `brainstorming`, then `/grill-me` if decisions are open, then spec |
| Approved design / spec exists | `writing-plans`, then `/grill-me` if decisions are open, then plan |
| Plan ready; implementation starts | `executing-plans` or `subagent-driven-development` |
| Bug, regression, failing test, unclear cause | `systematic-debugging` |
| Code change needing regression guard | `test-driven-development` only for meaningful coverage |
| Review requested | `requesting-code-review` |
| Branch ready to finish | `finishing-a-development-branch` only when user asked for branch finish flow |

Planning gate for large work:

1. Spec.
2. Human approval.
3. Plan.
4. Human approval.
5. Implement.

Design baseline (`/grill-me`): one question at a time. Explore the codebase when the answer is already there.

If a Superpowers skill conflicts with AGENTS.md on policy, user request and AGENTS.md win.

---

## Plan Execution Continuity

After plan approval, `executing-plans` or `subagent-driven-development` may run without pausing between routine plan tasks until the final review stage.

| Continue through tasks | Stop and ask the human |
| ---------------------- | ---------------------- |
| Per-task verification named in the plan | Missing dependency |
| Spec-then-quality review between tasks | Unclear plan step |
| Persona briefing once before first code edit | Repeated verification failure |
| Routine fixes within approved scope | Scope outside plan |
| | Safety or destructive action not covered by plan |
| | Plan-marked breakpoint |
| | User pauses or redirects |
| | Test creation required but not authorized |
| | Instruction conflict |

Final review starts only when every plan task is done.

Plan scope freeze: when plan tasks A, B, C are done, stop. No C-2/C-3 unless the user opens a new spec/plan cycle.

Branch completion: verify, report status, and use branch finish flow only when the user asks or the approved plan includes that step.

---

## Persona Dialogue

Persona is an optional lens, not a default ceremony.

For non-trivial `src/` / `tests/` work when useful:

1. Coordinator summarizes and assigns once.
2. Owner persona gives a 1-2 sentence approach once before the first code edit in a plan run.
3. Implement.

After code: run the smallest meaningful verification. Full persona verification flow is only for tests or full-gate tasks.

Details: `.cursor/rules/20-persona-dialogue.mdc`, `persona/README.md`.

---

## Spec & Plan File Naming

Required for new specs, plans, and roadmaps. Legacy docs are grandfathered.

Rename allowed when:

1. The doc is active and canonical.
2. Implementation has not started, or all links can be updated atomically.
3. The rename and inbound-link updates happen together.

Directory-local `NNN`:

| Directory | Rule |
| --------- | ---- |
| `specs/` | highest existing + 1 |
| `plans/` | highest existing + 1 |
| `roadmap/` | highest existing + 1 |

Spec and plan numbers are independent.

### Spec

```text
NNN-YYYY-MM-DD-<kind>-<layer>-<area>-<topic>-design.md
```

### Plan

```text
NNN-YYYY-MM-DD-<kind>-<layer>-<area>-prNN-<topic>.md
```

`prNN` is plan-only.

### Roadmap

```text
NNN-YYYY-MM-DD-<area>-<topic>-roadmap.md
```

### Taxonomy

| Segment | Values |
| ------- | ------ |
| `<kind>` | `bugfix` \| `dev` \| `feature` \| `refactor` \| `docs` \| `infra` |
| `<layer>` | `ui` \| `backend` \| `bridge` \| `domain` \| `fullstack` \| `infra` \| `docs` |
| `<area>` | `shell` \| `scan` \| `duplicate` \| `move` \| `finalize` \| `quality` \| `apply` \| `session` \| `file-dock` \| `logs` \| `settings` \| `platform` \| `release` |
| `<topic>` | kebab-case; no status words |

Layer vs area:

- `<layer>` is the primary code layer.
- `<area>` is the product/workflow region.
- `bridge` is a layer only.
- Pick the primary value when a slice spans multiple areas; note secondary scope in the body.

### Frontmatter

Required on new specs and plans:

```yaml
risk: safe | destructive | breaking
```

Default `safe`. Put `destructive` or `breaking` in the filename topic only when review must notice risk from the name alone.

### Do Not Put In Filenames

- `draft`
- `approved`
- `done`
- priority
- assignee
- parent spec paths
- LOCK ids
- `TEST_ALLOWED`
- other volatile metadata

### Examples

- `018-2026-06-02-feature-ui-shell-work-mode-tab-transition-design.md`
- `024-2026-06-02-feature-ui-shell-pr31-work-mode-tab-transition.md`
- `030-2026-06-02-feature-backend-apply-destructive-preview-guard-design.md`
- `003-2026-06-02-platform-release-roadmap.md`
