# Kanban (Kanban Markdown)

All agent work starts with Kanban intake on each user request ([00-user-request-kanban.mdc](../../.cursor/rules/00-user-request-kanban.mdc)). Roadmap work, implementation, destructive-risk, and cross-file design use this board. Entry: [AGENTS.md](../../AGENTS.md) · gates: `.cursor/rules/20-kanban-workflow.mdc` · detail: [KANBAN-detail.md](./KANBAN-detail.md) · ops: [KANBAN-ops.md](./KANBAN-ops.md).

## Pipeline (event-pipeline v2)

```text
Inbox → Spec Draft → Spec Review → Plan Draft → Plan Review → Todo → Scheduled → Ready Gate → In Progress → Verify → Done
Blocked — side column from any phase
```

Each column exit **creates a new card** at the next column (same `epic`). Prior cards stay for gap review. Product code only after **Ready Gate** passes → **In Progress** card.

## Locations

| What | Where |
|------|--------|
| Cards | [`.devtool/features/`](../../.devtool/features/) (`*.md` active, `done/*.md` completed) |
| Columns config | [`.vscode/settings.json`](../../.vscode/settings.json) → `kanban-markdown.columns` |
| Track / current PR | [KANBAN.yml](./KANBAN.yml) `meta` |
| Program pointer | [current_query.md](../superpowers/roadmap/current_query.md) |
| Roadmap narrative | `docs/superpowers/roadmap/*.md` |
| BACKLOG tickets | [BACKLOG.yml](./BACKLOG.yml) + card |

## Open board (humans)

VS Code/Cursor: install **Kanban Markdown** → command palette → **Open Kanban Board**.

## After moves

```bash
python scripts/kanban/sync_kanban_folders.py
```

**Board UI:** Kanban Markdown only lists `features/*.md` and `features/done/*.md`. Column = frontmatter `status`. Do not stash active cards under subfolders — the extension will not show them.

Done column: same-kind cards (PR/OPS + track) auto-merge into one **bundle** card ([KANBAN-ops](./KANBAN-ops.md#bulk-re-import)).

## See also

- [KANBAN-detail.md](./KANBAN-detail.md) — phases, card schema, approval, drift, automation triggers
- [KANBAN-ops.md](./KANBAN-ops.md) — bulk import, CLI skill, flow diagram
- [agent-workflow.md](../superpowers/agent-workflow.md) — large-work skill mapping
