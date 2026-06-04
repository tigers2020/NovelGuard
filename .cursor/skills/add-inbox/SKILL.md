---
name: add-inbox
description: >-
  Creates a NovelGuard Kanban Inbox card from a user request. Use when the user
  invokes /add-inbox, asks to add work to the Kanban inbox, triage a new item,
  or intake scope before spec/plan automation.
disable-model-invocation: true
---

# /add-inbox

Add a **new Inbox card** only. Do not write `src/` or `web/` code. Do not advance columns unless the user asks.

## When to use

- User: `/add-inbox …`, “add to kanban inbox”, “create an inbox card for …”
- New card-scoped work with no existing `work_id` on the board

If the request is full Kanban routing (active card, gates, implementation), use the [kanban](../kanban/SKILL.md) skill instead.

## Parse the request

Extract from the user message (ask only if blocking):

| Field | Required | Notes |
|-------|----------|--------|
| **Title** | yes | Short H1 title |
| **Scope** | yes | Problem, constraints, links |
| **Acceptance** | yes | Testable done criteria — automation blocks without this |
| **files_allowed** | yes | Path prefixes; default `.devtool/features/`, `docs/agent/` if only docs/agent state |
| **work_id** | no | Default `{slug-from-title}-{YYYY-MM-DD}` |
| **work_type** | **yes** | `feature` \| `fix` \| `other` — see below |
| **track** / **spec** / **plan** | no | Roadmap table rows when known |
| **labels** / **priority** | no | Extra labels only (e.g. `backlog`); `work_type` is auto-tagged |

### work_type (required tag)

Set on every Inbox card as frontmatter `work_type` and first entry in `labels`.

| Value | When to use | User phrases (examples) |
|-------|-------------|-------------------------|
| **feature** | New capability, UX change, enhancement | “add”, “implement”, “support”, “새 기능”, “기능 개발” |
| **fix** | Broken behavior, regression, incorrect output | “bug”, “broken”, “fix”, “regression”, “버그”, “수정” |
| **other** | Docs-only, refactor, ops, spike, tooling, hygiene | “refactor”, “chore”, “docs”, “cleanup”, “그외”, “기타” |

If unclear from the message, ask once: *feature, fix, or other?* Do not create the card without `work_type`.

## Create the card (preferred)

From repo root:

```bash
python scripts/kanban/kanban_add_inbox.py "Short title" \
  --work-type feature \
  --acceptance "Done when …" \
  --scope "Problem and constraints …" \
  --files-allowed .devtool/features/ docs/agent/ web/src/
```

`--work-type` is required: `feature`, `fix`, or `other`.

Optional flags: `--work-id`, `--track`, `--spec`, `--plan`, `--labels`, `--priority`, `--dry-run`.

- **Exit 0** — prints relative card path; use it in closeout.
- **Exit 2** — duplicate `work_id` or inbox; report blocker, do not overwrite.

## Manual write (if script unavailable)

Path: `.devtool/features/{work_id}-inbox.md`

Frontmatter minimum:

```yaml
---
id: {work_id}-inbox
status: inbox
work_id: {work_id}
epic: {work_id}
work_type: feature   # feature | fix | other
labels:
  - feature
priority: medium
created: "<ISO-8601 Z>"
acceptance: "<one-line summary>"
files_allowed:
  - .devtool/features/
  - docs/agent/
automation_state: created
---
```

Body minimum: `# Title`, roadmap table with **Type** row, `## Scope`, `## Acceptance`, `## files_allowed`. Optional `Track` / `Spec` / `Plan` per [KANBAN-ops.md](../../docs/agent/KANBAN-ops.md).

## After create

1. If legacy column subfolders exist under `.devtool/features/`, run:
   `python scripts/kanban/sync_kanban_folders.py`
2. Do **not** run `kanban_inbox_to_scheduled.py` unless the user requests automation.
3. Reply with closeout:

```text
## Inbox added
- Card: <work_id> @ inbox
- Type: feature | fix | other
- Path: .devtool/features/<work_id>-inbox.md
- Acceptance: <summary>
- files_allowed: …
- Next: edit card if needed; run kanban-inbox-to-scheduled.bat or /Kanban when ready to plan
```

## Rules

- **One inbox per `work_id`** — search board before create (`ensure_unique_card` / script exit 2).
- Inbox column: scope and metadata only — no spec drafting, no product code ([KANBAN-detail.md](../../docs/agent/KANBAN-detail.md)).
- Use today’s date in default `work_id` unless the user supplies one.
- English for card content unless the user writes in another language.

## Examples

**User:** `/add-inbox Column chooser should persist per work mode`

```bash
python scripts/kanban/kanban_add_inbox.py "Column chooser persistence per work mode" \
  --work-type feature \
  --acceptance "Resolve and Quality grids restore visible columns per mode after restart." \
  --scope "Persist TanStack column visibility in settings; no server changes." \
  --files-allowed web/src/ .devtool/features/
```

**User:** `/add-inbox fix: duplicate keeper not applied after move`

```bash
python scripts/kanban/kanban_add_inbox.py "Duplicate keeper not applied after move" \
  --work-type fix \
  --acceptance "After move preview apply, keeper file matches user selection." \
  --scope "Resolve apply path; regression test in bridge contract suite." \
  --files-allowed src/ web/src/
```

**User:** `/add-inbox pr-58 — export audit log` with explicit id:

```bash
python scripts/kanban/kanban_add_inbox.py "Export audit log" \
  --work-type feature \
  --work-id pr-58-2026-06-04 \
  --acceptance "Settings → Logs exports JSON/CSV of audit entries for current library." \
  --scope "Bridge + UI only; document privacy in spec later." \
  --files-allowed web/src/ src/
```
