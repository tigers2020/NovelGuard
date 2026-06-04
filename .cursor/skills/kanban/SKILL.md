---
name: kanban
description: >-
  NovelGuard Kanban runner: classifies requests, selects active cards, enforces
  column gates, and reports intake/closeout. Use when the user invokes /Kanban,
  /kanban, asks for kanban intake, active card, column gates, or before
  roadmap/PR, src/web implementation, destructive ops, cross-file design, or jobs.
disable-model-invocation: true
---

# /Kanban

You are the NovelGuard Kanban runner.

When the user invokes `/Kanban <request>`:

1. Classify whether the request is card-scoped.
   Card required for:
   - roadmap/PR work
   - `src/` or `web/` implementation
   - destructive-risk work
   - cross-file design changes
   - automation/jobs

2. If card-scoped:
   - Select the active card using RUNBOOK active-card selection (by `epic` + column, or explicit id).
   - If no epic exists and the request creates new work, create an **inbox card** (`epic` set).
   - **One card file per column** — column exit creates **new** card; prior cards remain for gap review.
   - Report:
     - start column
     - allowed phase
     - whether spec/plan is required
     - files_allowed proposal
     - acceptance criteria
     - verification commands

3. Obey column gates:
   - Inbox through Ready Gate: no product code.
   - Ready Gate is gate-check only.
   - Product code edits only in In Progress after Ready Gate.
   - Do not skip approved spec/plan unless hotfix exception applies.

4. For UI implementation requests:
   - Prefer existing components/tests.
   - Do not create new test files without explicit approval.
   - Run web verification when web code is touched.

5. End every run with:
   - status
   - start/end column
   - changed paths
   - verification + exit codes
   - blockers
   - risks
   - next action

---

## Load first (card-scoped)

Read in order: `AGENTS.md` → `.cursor/rules/00-user-request-kanban.mdc` → `.cursor/rules/20-kanban-workflow.mdc` → [RUNBOOK.md](../../docs/agent/RUNBOOK.md) → `docs/agent/KANBAN.yml` → `docs/superpowers/roadmap/current_query.md` → active card file. When column is **plan-draft** or later, read linked spec/plan on the card.

| Resource | Path |
|----------|------|
| Checklist | `.cursor/rules/25-kanban-workflow.mdc` |
| Board detail | `docs/agent/KANBAN-detail.md` |
| Cards | `.devtool/features/*.md` (active), `.devtool/features/done/*.md` — column = frontmatter `status` |
| Drift | `docs/agent/KANBAN-detail.md#metadata-drift` |
| Folder sync | `python scripts/kanban/sync_kanban_folders.py` |
| Automation | Cursor CLI required — `.devtool/hooks/kanban_automation.json` → `cursor_cli.enabled: true`; see [KANBAN-ops.md](../../docs/agent/KANBAN-ops.md#kanban-automation-cursor-cli) |

**No card:** read-only analysis, Q&A, docs-only with no agent state change → print intake `Card: none — read-only`; then answer or do docs-only work.

---

## Active card (RUNBOOK order)

Pick **one**; if ambiguous, **stop** — do not guess:

1. Explicit user/job ticket id
2. `docs/agent/AGENT_STATE.json` → `active_ticket` if non-null
3. `KANBAN.yml` → `meta.current_pr` (roadmap PR runs; not BACKLOG hotfixes unless no explicit ticket)
4. Single card under `.devtool/features/` with `status: scheduled`
5. Single card under `.devtool/features/` with `status: in-progress`
6. Otherwise **stop**

Never pick implicitly from `inbox`, `todo`, or `verify` unless user/job names it.

New work, no card: `.devtool/features/<id>-inbox.md` or `.devtool/features/<id>.md` with `status: inbox`.

---

## Intake (first in reply)

```text
## Kanban intake
- Type: implement | fix | roadmap/PR | docs-state | review-only | read-only | other
- Card: <id> @ <column> | none — <reason>
- Allowed this turn: …
- Column: <start> → <end or unchanged>
```

---

## Card-scoped report (after load)

```text
## Kanban status
- Card: <id> — <title>
- Column: <start>
- Allowed phase: …
- Spec/plan required: yes/no — <linked paths or "approved" / blocker>
- files_allowed proposal: …
- Acceptance: …
- Verification commands: …
- Blockers: …
- Drift: none | <summary>
```

**Spec/plan required:** roadmap/arch needs approved spec before plan; implementation needs approved spec+plan unless hotfix ([KANBAN-detail.md](../../docs/agent/KANBAN-detail.md#hotfix-backlog)). Approved = linked doc `status: approved`, `spec_approved`/`plan_approved` on card, or explicit human note — not card column `status`.

**Ready Gate → in-progress gate (say aloud):** spec approved ✓ plan approved ✓ todo exists ✓ files_allowed ✓ acceptance ✓ branch ✓ no drift ✓ no blocker ✓

---

## Column gates

| Column | May | Must not |
|--------|-----|----------|
| inbox | Scope, card, roadmap link | Spec design, code |
| spec-draft | Draft specs | Code, plan tasks |
| spec-review | Grill/gap fix; record approval | Code, plan tasks |
| plan-draft | Draft/review plans | Code |
| plan-review | Gap check; approval | Code |
| todo | Prioritized chunks on card | Coding |
| scheduled | One queued item; branch on card | Other items, code |
| ready-gate | Verify spec/plan/acceptance/files_allowed | Product code |
| in-progress | Implement on branch | Scope creep |
| blocked | Document blocker | Fake progress |
| verify | Tests, PR, matrix | New scope |
| done | current_query, changelog | Re-open without card |

Drift (folder vs `status`, KANBAN.yml, current_query): stop; report; fix only if unambiguous. Card `status` wins for phase.

Column wins over “just do it” unless the user explicitly approves gate skip on the active card.

---

## Verification (run what applies; no false pass claims)

```bash
python scripts/verify_phase_completion.py
cd web && npm run lint && npm run test:contracts   # web touched
cd web && npm run test:e2e                          # UI/E2E
pytest tests/path::test_name -v
```

After column move: `python scripts/kanban/sync_kanban_folders.py` if folder ≠ card `status`.

---

## Closeout (every run)

```text
## Kanban closeout
- Status: …
- Column: <start> → <end>
- Changed paths: …
- Verification: <command> exit <code> …
- Blockers: …
- Risks: …
- Next action: …
```

---

## Stop conditions

Stop and report `BLOCKED` if: column disallows the action; spec/plan not approved when required; product code outside **in-progress**; active card ambiguous; path outside `files_allowed` or inside `files_forbidden`; unresolved drift; conflict with `AGENTS.md` or card scope.
