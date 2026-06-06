# Migrate automation: todo-list → task-list (with legacy aliases)

**Date:** 2026-06-05  
**Status:** Draft — do not implement until terminology commit is on branch and cycle-smoke passes  
**Depends on:** `[automation] clarify task-list terminology and subagent-only implementation`

---

## Problem

Policy now says **Task list** (post-plan implementation tasks) and **`/subagent-driven-development` only** for implement. Wire names still use **todo-list** (`write-todo-list.md`, `auto:todo-list-done`, `todo_list_done`). Operators and logs stay confusing until aliases exist.

## Goal

Add **task-list** names everywhere operators read them, while **legacy todo-list identifiers keep working** until a later removal slice.

## Non-goals

- Breaking webhook routing for in-flight Linear issues
- Hard-deleting legacy label UUIDs or prompt paths in slice 1
- Renaming Cursor TodoWrite (IDE feature)

---

## Compatibility principle

```text
add new name → accept legacy alias → tests for both → deprecate → remove (later)
```

Never rename-only in one step.

---

## Scope

### 1. Linear label

| New | Legacy (keep) |
|-----|----------------|
| `auto:task-list-done` (new UUID in Linear) | `auto:todo-list-done` |

**Router:** `has_label_key` accepts either `task_list_done` or `todo_list_done` config key mapping to respective UUIDs. Routing reason string may say `task-list-done→implement` when new label fires; legacy reason unchanged.

### 2. Config (`automation/config.yaml`)

```yaml
linear:
  label_ids:
    task_list_done: <new-uuid>
    todo_list_done: 75d4a692-...   # legacy alias, same routing
```

`linear_ids.py`: `DEFAULT_LABEL_IDS` adds `task_list_done`; `todo_list_done` remains.

### 3. Prompt file

| New path | Legacy alias |
|----------|----------------|
| `linear/todo/write-task-list.md` | `linear/todo/write-todo-list.md` (symlink, router map, or `job_worker._LEGACY_PROMPT_ALIASES`) |

`resolve_planning_prompt` returns new path; `_resolve_prompt_file` resolves old path if enqueued from stale job.

Frontmatter `phase: write-task-list` (already in policy commit).

### 4. Router semantic keys

Rename internal references gradually:

- `_route_execution_from_labels`: check `task_list_done` first, fall back `todo_list_done`
- Reason strings: prefer `task-list-done→implement`; keep parsing tests for old substring optional

### 5. Cycle smoke

- Add fixtures `B1-task-list-done.json` **or** rename with manifest note `legacy_id: B1-todo-list-done`
- Expect reason may include either substring during transition

### 6. Tests

- `tests/test_linear_router.py`: legacy label UUID still routes implement
- New test: `task_list_done` UUID routes same prompt
- `tests/test_prompt_templates.py`: both prompt paths resolve to task-list content

### 7. Documentation

- `docs/agent-automation.md`: table shows `write-task-list.md` primary, legacy path in footnote
- Deprecation note: `auto:todo-list-done` removed after date TBD

---

## Rollout order

1. Create Linear label `auto:task-list-done`; add UUID to config (both keys)
2. Add `write-task-list.md` (copy from `write-todo-list.md`); wire router + legacy alias
3. Update router + tests (dual-key)
4. Update cycle-smoke manifest/fixtures
5. Update `config.example.yaml`
6. Operator doc: new issues should use `auto:task-list-done` on closeout; old issues still work

## Verification

```bash
pytest tests/test_linear_router.py tests/test_cycle_smoke.py tests/test_prompt_templates.py -q
python scripts/automation_cycle_smoke.py --all
```

Manual: webhook fixture with new label UUID → `implement.md` queued.

## Risks

| Risk | Mitigation |
|------|------------|
| Duplicate jobs (both labels on issue) | Router treats both as same phase; dedupe by prompt file stem |
| Stale jobs reference old `prompt_file` | `_LEGACY_PROMPT_ALIASES` in `job_worker.py` |
| Linear MCP `save_issue` uses wrong label | Update write-task-list closeout to prefer new label; document fallback |

## Success criteria

- New issues can close Task list phase with `auto:task-list-done`
- Old issues with `auto:todo-list-done` still route to implement
- No change required to webhook UUID maps for unrelated labels
- Cycle smoke 11/11 (or expanded count) passes
