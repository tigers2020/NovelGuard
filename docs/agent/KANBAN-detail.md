# Kanban detail (agents)

[KANBAN.md](./KANBAN.md) · [AGENTS.md](../../AGENTS.md).

## User request intake

Mandatory on every user work ask ([00-user-request-kanban.mdc](../../.cursor/rules/00-user-request-kanban.mdc)): classify → card? → column → allowed this turn → then act. Read-only Q&A: intake with no card; no `src/`/`web/` edits without **in-progress** after Ready Gate.

## Event-pipeline model

Each column exit **creates a new card** at the next column. Prior cards remain for audit and gap review — do not delete spec/plan cards; mark `lifecycle: consumed` on Done if needed.

```text
Inbox card created        → Spec Draft card created
Spec Draft exit           → Spec Review card created
Spec Review approved      → Plan Draft card created
Plan Draft exit           → Plan Review card created
Plan Review approved      → Todo card created
Todo exit                 → Scheduled card created
Scheduled selected        → Ready Gate card created
Ready Gate passed         → In Progress card created
In Progress completed     → Verify card created
Verify passed             → Done
```

## Phase guide

| Column | Do | Exit |
|--------|-----|------|
| Inbox | Slice, roadmap, labels, files_allowed draft | → Spec Draft |
| Spec Draft | Draft `specs/*-design.md` or card-body spec | → Spec Review |
| Spec Review | Grill/gap fix; record approval | approved → Plan Draft |
| Plan Draft | Draft `plans/*`; tasks, files_allowed | → Plan Review |
| Plan Review | Spec↔plan gap check; approval | approved → Todo |
| Todo | Priorities on card | → Scheduled |
| Scheduled | **One** item; spec+plan linked | selected → Ready Gate |
| Ready Gate | Gate-check: spec↔plan↔acceptance; branch; files_allowed — **no product code** | passed → In Progress |
| In Progress | **`src/`/`web/`** product code on branch | completed → Verify |
| Verify | Tests, PR, gap matrix | passed → Done; fail → In Progress |
| Blocked | Record blocker | → prior column |
| Done | current_query, changelog | — |

No `src/`/`web/` in inbox–ready-gate. Product code only in **in-progress**. One scheduled item/run.

## Card schema

**One card file per column per work item.** Frontmatter: `id`, `status` (column only), `epic` (shared work id), `priority`, `labels`. Optional approval fields: `spec_approved`, `plan_approved`, `approved_by`, `approved_at`. Link chain in body. Plan-review card: gap table vs spec card. Verify card: gap matrix spec↔plan↔implementation. Do **not** merge all phases into one card.

## Approval

**Approved spec/plan** = linked spec/plan document frontmatter `status: approved`, card frontmatter `spec_approved: true` / `plan_approved: true`, or explicit human approval on the active card. Card `status` (e.g. `ready-gate`) is **not** spec/plan approval. Drafts ≠ gates.

## Metadata drift

Folder, card `status`, [KANBAN.yml](./KANBAN.yml), [current_query](../superpowers/roadmap/current_query.md) mismatch → stop; report values; fix only if clear (`sync_kanban_folders.py` flattens to extension layout: active at `features/`, done at `features/done/`); else ask human. **Card `status` wins** for phase; current_query = orientation.

## Hotfix (BACKLOG)

Card `labels` must include `backlog`. Skip **spec/plan documents** only when card is already at **ready-gate** or **in-progress**, with `files_allowed` + acceptance on the card, and no arch/UX contract change. **Does not** skip inbox→ready-gate column walk (those exits still apply except spec/plan doc approval).

## Superpowers

| Column | Skills |
|--------|--------|
| spec-draft | brainstorming |
| spec-review | grill-me, grill-with-docs |
| plan-draft | writing-plans |
| plan-review | grill-me, writing-plans |
| in-progress | executing-plans, subagent-driven-development |
| verify | requesting-code-review |

Automation scripts invoke these skills via Cursor CLI (`agent -p --trust`); see [KANBAN-ops](./KANBAN-ops.md#kanban-automation-cursor-cli).

[agent-workflow.md](../superpowers/agent-workflow.md)

## Legacy column migration

| Legacy | v2 column |
|--------|-----------|
| triage | inbox |
| spec | spec-draft or spec-review |
| plan | plan-draft or plan-review |
| ready | ready-gate |
| review | verify |

Run: `python scripts/kanban/migrate_kanban_columns_v2.py` then `python scripts/kanban/sync_kanban_folders.py`.
