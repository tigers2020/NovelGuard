# Todo-List → Task-List Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Introduce **task-list** wire names (`write-task-list.md`, `auto:task-list-done`, `task_list_done`) while **legacy todo-list identifiers keep routing** until a future removal slice.

**Architecture:** Add dual-key helpers in `linear_ids.py` (`has_task_list_done`, `task_list_done_label_ids`). Router and `resolve_planning_prompt` prefer new names; legacy UUID/path resolved via aliases. Canonical prompt `write-task-list.md`; `write-todo-list.md` removed from router output but kept resolvable for stale queue jobs. No hard deletes in this plan.

**Tech Stack:** Python 3.12, pytest, Linear label UUIDs in `automation/config.yaml`, existing `automation/linear/router.py`, cycle-smoke harness.

**Spec:** `docs/superpowers/specs/2026-06-05-automation-todo-to-task-list-migration-design.md`  
**Prerequisite:** commit `398fb4e` (`[automation] clarify task-list terminology and subagent-only implementation`) on branch.

---

## File map

| File | Responsibility |
|------|----------------|
| `automation/linear/linear_ids.py` | `task_list_done` default UUID; `has_task_list_done()`, `task_list_done_label_ids()` |
| `automation/linear/router.py` | Dual-key routing; `write-task-list.md` path; reason strings |
| `automation/prompts/linear/todo/write-task-list.md` | Canonical Task list phase prompt |
| `automation/prompts/linear/todo/write-todo-list.md` | Legacy stub → points readers to new file (or re-export) |
| `automation/runners/job_worker.py` | `_PROMPT_PATH_ALIASES` for stale `write-todo-list.md` jobs |
| `automation/config.example.yaml` | `task_list_done` + `todo_list_done` keys |
| `automation/examples/cycle-smoke/` | New fixture for `task_list_done` label |
| `tests/test_linear_router.py` | Legacy + new label routing tests |
| `tests/test_cycle_smoke.py` | Optional 12th case or dual reason assert |
| `tests/test_prompt_templates.py` | Both prompt paths valid |
| `tests/test_job_worker_prompt.py` | Stale path alias resolves |
| `docs/agent-automation.md` | Primary `write-task-list.md`, deprecation footnote |

---

### Task 0: Commit migration spec

**Files:**
- Create: `docs/superpowers/specs/2026-06-05-automation-todo-to-task-list-migration-design.md` (if uncommitted)

- [ ] **Step 1: Commit spec only**

```bash
git add docs/superpowers/specs/2026-06-05-automation-todo-to-task-list-migration-design.md
git commit -m "docs(automation): spec for todo-list to task-list migration with legacy aliases"
```

---

### Task 1: Linear label UUID (operator gate)

**Files:**
- Modify: `automation/config.yaml` (local, gitignored — operator)
- Modify: `automation/config.example.yaml`

**Operator action:** Create Linear label `auto:task-list-done` on team NovelGuard. Record UUID.

- [ ] **Step 1: Add placeholder to config.example.yaml**

Under `linear.label_ids`, add **above** `todo_list_done`:

```yaml
    task_list_done: "00000000-0000-4000-8000-000000000001"  # replace after creating auto:task-list-done in Linear
    todo_list_done: 75d4a692-8214-4592-8f45-f29f93162b45
```

- [ ] **Step 2: Update local automation/config.yaml**

Set `task_list_done` to the real UUID from Linear. Run:

```bash
python scripts/linear_sync_label_cache.py
```

Expected: `automation/labels/cache.json` includes new id→name entry (local only).

- [ ] **Step 3: Commit example config only**

```bash
git add automation/config.example.yaml
git commit -m "chore(automation): add task_list_done label slot to config example"
```

---

### Task 2: `linear_ids.py` dual-key helpers

**Files:**
- Modify: `automation/linear/linear_ids.py`
- Test: `tests/test_linear_router.py` (new tests at end)

- [ ] **Step 1: Write failing tests**

Append to `tests/test_linear_router.py`:

```python
_TASK_LIST_DONE_TEST = "aaaaaaaa-bbbb-4ccc-dddd-111111111111"
_LEGACY_TODO_LIST_DONE = DEFAULT_LABEL_IDS["todo_list_done"]


def _cfg_dual_task_list() -> dict:
    return {
        "linear": {
            "label_ids": {
                **dict(DEFAULT_LABEL_IDS),
                "task_list_done": _TASK_LIST_DONE_TEST,
            }
        }
    }


def test_has_task_list_done_accepts_new_label_uuid():
    from automation.linear.linear_ids import has_task_list_done

    data = {"labelIds": [_TASK_LIST_DONE_TEST]}
    assert has_task_list_done(data, _cfg_dual_task_list()) is True


def test_has_task_list_done_accepts_legacy_todo_list_done_uuid():
    from automation.linear.linear_ids import has_task_list_done

    data = {"labelIds": [_LEGACY_TODO_LIST_DONE]}
    assert has_task_list_done(data, _cfg_dual_task_list()) is True


def test_task_list_done_label_uuid_routes_implement():
    payload = {
        "action": "update",
        "type": "Issue",
        "updatedFrom": {"labelIds": ["f3424dcd-6d2c-47f9-a8fe-5f4d5b626d27"]},
        "data": {
            "identifier": "NOV-SMOKE",
            "teamId": "97047174-6453-4458-b170-a9bf5f7b52e0",
            "projectId": "20965ebc-3ea7-4787-9310-f15ad9019007",
            "stateId": "49a46ce6-eb18-4377-95ae-b76f655a77b7",
            "labelIds": [
                "f3424dcd-6d2c-47f9-a8fe-5f4d5b626d27",
                _TASK_LIST_DONE_TEST,
            ],
        },
    }
    route = route_linear_webhook(payload, cfg=_cfg_dual_task_list())
    assert route is not None
    assert route.prompt_file == "linear/todo/write-task-list.md"
    assert "task-list-done→implement" in route.reason
```

- [ ] **Step 2: Run tests — expect FAIL**

```bash
pytest tests/test_linear_router.py::test_has_task_list_done_accepts_new_label_uuid -v
```

Expected: FAIL — `has_task_list_done` not defined.

- [ ] **Step 3: Implement helpers in `linear_ids.py`**

Add to `DEFAULT_LABEL_IDS` (after `todo_list_done` line):

```python
    "task_list_done": "00000000-0000-4000-8000-000000000001",
```

Add functions before `route_debug`:

```python
_TASK_LIST_DONE_KEYS = ("task_list_done", "todo_list_done")


def task_list_done_label_ids(cfg: dict[str, Any] | None = None) -> frozenset[str]:
    merged = _merged_label_ids(cfg)
    ids: set[str] = set()
    for key in _TASK_LIST_DONE_KEYS:
        value = merged.get(key)
        if value and not str(value).startswith("00000000-0000-4000-8000-000000000001"):
            ids.add(str(value))
        elif key == "todo_list_done" and value:
            ids.add(str(value))
    return frozenset(ids)


def has_task_list_done(data: dict[str, Any], cfg: dict[str, Any] | None = None) -> bool:
    ids = task_list_done_label_ids(cfg)
    if not ids:
        return False
    return bool(ids & issue_label_ids(data))
```

Note: placeholder `00000000-…0001` is ignored so tests use injected UUID via cfg; production config must set real UUID.

Export in `__all__` if module has one.

- [ ] **Step 4: Run new id tests only**

```bash
pytest tests/test_linear_router.py::test_has_task_list_done_accepts_new_label_uuid tests/test_linear_router.py::test_has_task_list_done_accepts_legacy_todo_list_done_uuid -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add automation/linear/linear_ids.py tests/test_linear_router.py
git commit -m "feat(automation): add dual-key task_list_done label helpers"
```

---

### Task 3: Canonical `write-task-list.md` + legacy path alias

**Files:**
- Create: `automation/prompts/linear/todo/write-task-list.md`
- Modify: `automation/prompts/linear/todo/write-todo-list.md`
- Modify: `automation/prompts/linear/backlog/grill-plan.md` (next-step path)
- Modify: `automation/runners/job_worker.py`
- Test: `tests/test_job_worker_prompt.py`

- [ ] **Step 1: Create `write-task-list.md`**

Copy current `write-todo-list.md` and update closeout block:

```markdown
**Entry:** Todo + `auto:plan-done` · **Exit:** In Progress + `auto:task-list-done` (preferred; legacy `auto:todo-list-done` still routes)

...

| `auto:task-list-done` or `auto:todo-list-done` + no `regenerate task` | idempotent exit |

...

**Closeout — MUST** — `save_issue(state=In Progress, labels+=auto:task-list-done)` **one call**. If label missing in workspace, use `auto:todo-list-done`. STOP. → `linear/in-progress/implement.md`.
```

- [ ] **Step 2: Replace `write-todo-list.md` with legacy pointer**

Keep file so old links work; minimal content:

```markdown
---
trigger: linear.labels@Todo
label: auto:plan-done
phase: write-task-list
deprecated: use linear/todo/write-task-list.md
---

@linear/todo/write-task-list.md

> **Legacy path.** Automation router enqueues `write-task-list.md`. This file remains for stale jobs and bookmarks.
```

(Cursor may not resolve `@linear/...` — instead duplicate frontmatter + include same body as write-task-list OR keep full duplicate; **preferred:** keep **identical body** to `write-task-list.md` with one-line HTML comment `<!-- legacy path alias -->` at top so render works without @include.)

**Use identical copy** of `write-task-list.md` plus first line:

```markdown
<!-- legacy prompt path: prefer write-task-list.md -->
```

- [ ] **Step 3: Write failing job_worker alias test**

Append to `tests/test_job_worker_prompt.py`:

```python
def test_resolve_legacy_write_todo_list_prompt_path(tmp_path):
    from automation.runners.job_worker import _resolve_prompt_file
    from automation.runners.config import repo_root

    prompts_dir = repo_root() / "automation" / "prompts"
    resolved = _resolve_prompt_file(
        prompts_dir, "linear/todo/write-todo-list.md"
    )
    assert resolved == "linear/todo/write-todo-list.md"
    assert (prompts_dir / resolved).is_file()
```

- [ ] **Step 4: Add path alias in `job_worker.py`**

After `_LEGACY_PROMPT_ALIASES`, add:

```python
_PROMPT_PATH_ALIASES: dict[str, str] = {
    "linear/todo/write-todo-list.md": "linear/todo/write-task-list.md",
}
```

In `_resolve_prompt_file`, after direct file check fails:

```python
    path_alias = _PROMPT_PATH_ALIASES.get(prompt_file)
    if path_alias and (prompts_dir / path_alias).is_file():
        return path_alias
```

- [ ] **Step 5: Update grill-plan.md references**

Replace `linear/todo/write-todo-list.md` with `linear/todo/write-task-list.md` in both STOP lines.

- [ ] **Step 6: Run tests**

```bash
pytest tests/test_job_worker_prompt.py tests/test_prompt_templates.py -q
```

Expected: all PASS.

- [ ] **Step 7: Commit**

```bash
git add automation/prompts/linear/todo/write-task-list.md automation/prompts/linear/todo/write-todo-list.md automation/prompts/linear/backlog/grill-plan.md automation/runners/job_worker.py tests/test_job_worker_prompt.py
git commit -m "feat(automation): add write-task-list prompt with legacy path alias"
```

---

### Task 4: Router dual-key + planning path

**Files:**
- Modify: `automation/linear/router.py`
- Test: `tests/test_linear_router.py`

- [ ] **Step 1: Update `resolve_planning_prompt`**

Change plan_done branch:

```python
        if has_label_key(data, cfg, "plan_done"):
            return "linear/todo/write-task-list.md"
```

- [ ] **Step 2: Replace `todo_list_done` checks in `_route_execution_from_labels`**

Replace:

```python
    if has_label_key(data, cfg, "todo_list_done"):
```

With:

```python
    if has_task_list_done(data, cfg):
```

Add import: `from automation.linear.linear_ids import has_task_list_done, task_list_done_label_ids`

Update reason fragment:

```python
                reason=f"{reason_prefix} (task-list-done→implement)",
```

When only legacy UUID present, optional: keep `todo-list-done→implement` if `has_label_key(data, cfg, "todo_list_done") and not has_label_key(data, cfg, "task_list_done")` — else prefer `task-list-done→implement`.

- [ ] **Step 3: Update `_route_label_only_execution`**

Replace `todo_list_done_id` block with:

```python
    done_ids = task_list_done_label_ids(cfg)
    if done_ids:
        newly_done = [lid for lid in done_ids if lid in current and lid not in before]
        if newly_done and not has_label_key(data, cfg, "verify_done"):
            legacy_only = all(
                lid == str(merged.get("todo_list_done") or DEFAULT_LABEL_IDS.get("todo_list_done") or "")
                for lid in newly_done
            )
            suffix = "todo-list-done→implement" if legacy_only else "task-list-done→implement"
            return LinearRoute(
                prompt_file=_PROMPT_IMPLEMENT,
                commit=True,
                verify="none",
                git_prepare=False,
                reason=f"labels@{state} ({suffix})",
            )
```

- [ ] **Step 4: Run router tests**

```bash
pytest tests/test_linear_router.py -q
```

Expected: all PASS (update `test_label_ids_only` expect path if it asserted `write-todo-list.md`):

In `test_label_ids_only_routes_by_uuid`, change:

```python
    assert route.prompt_file == "linear/todo/write-task-list.md"
```

In `test_status_todo_todo_list_done_routes_implement_over_planning`, accept either reason substring:

```python
    assert "list-done→implement" in route.reason
```

- [ ] **Step 5: Run failing test from Task 2 Step 1**

```bash
pytest tests/test_linear_router.py::test_task_list_done_label_uuid_routes_implement -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add automation/linear/router.py tests/test_linear_router.py
git commit -m "feat(automation): router accepts task_list_done and legacy todo_list_done"
```

---

### Task 5: Cycle-smoke fixture for new label

**Files:**
- Create: `automation/examples/cycle-smoke/B1-task-list-done.json`
- Modify: `automation/examples/cycle-smoke/manifest.json`
- Modify: `automation/examples/cycle-smoke/B1-todo-list-done.json` (add comment in manifest only)

- [ ] **Step 1: Add fixture `B1-task-list-done.json`**

Same as `B1-todo-list-done.json` but swap `75d4a692-8214-4592-8f45-f29f93162b45` → `aaaaaaaa-bbbb-4ccc-dddd-111111111111` in `labelIds` (test UUID; manifest documents that production uses real UUID from config).

For smoke runner, inject test cfg — **better:** add optional `cfg_override` in manifest case OR use `DEFAULT_LABEL_IDS` task_list_done after Task 2 sets real default.

**Approach:** In `cycle_smoke.run_case`, pass `_cfg_dual_task_list()` from tests only; for CLI smoke, fixture uses **legacy** UUID (existing B1) and new case uses config's `task_list_done` when set.

Create `B1-task-list-done.json`:

```json
{
  "action": "update",
  "type": "Issue",
  "webhookId": "smoke-b1-task",
  "updatedFrom": {
    "labelIds": ["f3424dcd-6d2c-47f9-a8fe-5f4d5b626d27"]
  },
  "data": {
    "identifier": "NOV-SMOKE",
    "url": "https://linear.app/example/issue/NOV-SMOKE",
    "teamId": "97047174-6453-4458-b170-a9bf5f7b52e0",
    "projectId": "20965ebc-3ea7-4787-9310-f15ad9019007",
    "stateId": "49a46ce6-eb18-4377-95ae-b76f655a77b7",
    "labelIds": [
      "f3424dcd-6d2c-47f9-a8fe-5f4d5b626d27",
      "aaaaaaaa-bbbb-4ccc-dddd-111111111111"
    ]
  }
}
```

- [ ] **Step 2: Extend `cycle_smoke.py` test cfg hook**

Add module-level smoke test cfg used when env `CYCLE_SMOKE_TEST_LABELS=1` or always merge test UUID in `run_manifest` when `task_list_done` in config is placeholder.

**Minimal:** In `tests/test_cycle_smoke.py`, pass cfg:

```python
def _smoke_cfg():
    from tests.test_linear_router import _cfg_dual_task_list
    base = load_config()
    base.setdefault("linear", {})["label_ids"] = _cfg_dual_task_list()["linear"]["label_ids"]
    return base
```

Update `test_full_manifest` to use `_smoke_cfg()` and bump count to 12 after manifest entry added.

- [ ] **Step 3: Add manifest case**

```json
        {
          "id": "B1-task-list-done",
          "fixture": "B1-task-list-done.json",
          "expect_prompt": "linear/in-progress/implement.md",
          "expect_reason_contains": "task-list-done→implement"
        },
```

Keep existing `B1-todo-list-done` with `expect_reason_contains": "todo-list-done→implement"`.

- [ ] **Step 4: Run cycle smoke**

```bash
pytest tests/test_cycle_smoke.py -q
python scripts/automation_cycle_smoke.py --all
```

Note: CLI may fail new case until local `config.yaml` sets `task_list_done` to `aaaaaaaa-...` OR cycle_smoke loads dual cfg — document that **pytest uses injected cfg**; CLI requires config update (Task 1 Step 2).

- [ ] **Step 5: Commit**

```bash
git add automation/examples/cycle-smoke/ automation/runners/cycle_smoke.py tests/test_cycle_smoke.py
git commit -m "test(automation): cycle-smoke coverage for task_list_done label"
```

---

### Task 6: Prompt template guard + docs

**Files:**
- Modify: `tests/test_prompt_templates.py`
- Modify: `docs/agent-automation.md`

- [ ] **Step 1: Add prompt path test**

Append to `tests/test_prompt_templates.py`:

```python
def test_write_task_list_prompt_exists():
    path = PROMPTS / "todo" / "write-task-list.md"
    assert path.is_file()
    text = path.read_text(encoding="utf-8")
    assert "## Task list" in text
    assert "auto:task-list-done" in text


def test_legacy_write_todo_list_still_exists():
    path = PROMPTS / "todo" / "write-todo-list.md"
    assert path.is_file()
```

- [ ] **Step 2: Update `docs/agent-automation.md`**

Table row:

```markdown
| Todo + `auto:plan-done` | `todo/write-task-list.md` (legacy path `write-todo-list.md` still resolves) |
```

Add deprecation note:

```markdown
**Deprecation:** `auto:todo-list-done` and `write-todo-list.md` remain accepted; new closeouts should use `auto:task-list-done`.
```

- [ ] **Step 3: Commit**

```bash
git add tests/test_prompt_templates.py docs/agent-automation.md
git commit -m "docs(automation): document task-list primary paths and legacy aliases"
```

---

### Task 7: Final verification gate

- [ ] **Step 1: Full pytest**

```bash
pytest tests/test_linear_router.py tests/test_cycle_smoke.py tests/test_prompt_templates.py tests/test_job_worker_prompt.py -q
```

Expected: all passed (12 cycle-smoke cases in pytest with injected cfg).

- [ ] **Step 2: Cycle smoke CLI (with local config)**

Ensure `automation/config.yaml` has:

```yaml
    task_list_done: "aaaaaaaa-bbbb-4ccc-dddd-111111111111"  # or real Linear UUID
```

```bash
python scripts/automation_cycle_smoke.py --all
```

Expected: `"failed": 0`, `"total": 12`.

- [ ] **Step 3: Compile**

```bash
python -m compileall automation/linear automation/runners/cycle_smoke.py
```

Expected: exit `0`.

- [ ] **Step 4: Commit plan doc**

```bash
git add docs/superpowers/plans/2026-06-05-automation-todo-to-task-list-migration.md
git commit -m "docs(automation): implementation plan for task-list migration"
```

---

## Spec coverage checklist

| Spec requirement | Task |
|------------------|------|
| New Linear label `auto:task-list-done` | Task 1 |
| Legacy `auto:todo-list-done` accepted | Task 2, 4 |
| `write-task-list.md` + legacy alias | Task 3 |
| `task_list_done` config + fallback | Task 1, 2 |
| Router dual-key | Task 4 |
| Cycle-smoke | Task 5 |
| Tests both paths | Task 2, 4, 5, 6 |
| Deprecation docs | Task 6 |
| No hard delete | All tasks |

## Out of scope (future slice)

- Remove `todo_list_done` from config
- Delete `write-todo-list.md`
- Remove `auto:todo-list-done` from Linear
