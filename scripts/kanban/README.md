# Kanban scripts

Local board automation and maintenance for `.devtool/features/`.

## Layout

| Script | Role |
|--------|------|
| `kanban_common.py` | Shared helpers (cards, columns, Cursor CLI, locks) |
| `kanban_add_inbox.py` | Create inbox card |
| `kanban_inbox_to_scheduled.py` | Inbox → scheduled automation |
| `kanban_scheduled_to_inprogress.py` | Scheduled → in-progress automation |
| `kanban_verify_gate.py` | Verify → done / in-progress |
| `sync_kanban_folders.py` | Flatten legacy subfolders; bundle `done/` |
| `bundle_done_kanban_cards.py` | Merge done cards by track/kind |
| `fix_kanban_card_links.py` | Normalize spec/plan link paths |
| `migrate_kanban_columns_v2.py` | One-time v1 → v2 column migration |
| `migrate_roadmap_to_kanban.py` | Import from `KANBAN.full.yml` |
| `rehydrate_planning_cards.py` | Regenerate generic plan/todo from spec |

All Kanban scripts live under `scripts/kanban/` only (no repo-root duplicates).

## Common commands

```bash
python scripts/kanban/sync_kanban_folders.py
python scripts/kanban/sync_kanban_folders.py --dry-run
python scripts/kanban/kanban_add_inbox.py "Title" --work-type feature --acceptance "…"
```

Automation (poll): see repo-root `kanban-*.bat` and [KANBAN-ops.md](../../docs/agent/KANBAN-ops.md).

Config: `.devtool/hooks/kanban_automation.json`.
