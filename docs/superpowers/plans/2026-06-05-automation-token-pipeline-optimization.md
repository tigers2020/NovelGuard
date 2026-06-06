# Automation Token Pipeline Optimization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cut Cursor pre-cache token growth for Linear webhook jobs by shrinking prompts, compressing cross-job context with local Ollama (`gemma4:latest`), and wiring existing stall detection — without moving routing decisions back into AI prompts.

**Architecture:** Keep **Python `router.py` as control plane** (already UUID + label-driven on `e7e466a`). Add a **context compressor sidecar** that turns issue/history/log inputs into a small JSON memory block injected at `render_prompt()` time. Replace full `@runner-brief.md` includes in phase prompts with a compact inline brief. Wire **untracked** `cursor_stall.py` into `process_job()` for hung-agent recovery. Default `context_compressor.enabled: false` until doctor script passes.

**Tech Stack:** Python 3.12, pytest, Ollama HTTP API (`/api/generate`, JSON format), existing `automation/runners/job_worker.py`, `automation/linear/router.py`, gemma4:latest per `automation/config.yaml`.

**Baseline (do not re-implement):** `e7e466a` — `linear_ids.py`, UUID webhook routing, label-driven execution (`impl-done→verify`, `todo-list-done→implement`), `msvcrt` repo lock, daemon queue reuse, regression test `test_router_committed_surface_uses_uuid_routing`.

---

## File map

| File | Responsibility |
|------|----------------|
| `automation/linear/router.py` | Shorter `build_job_payload().task` string |
| `docs/agents/runner-brief-compact.md` | ~40-line headless safety/verify summary |
| `automation/prompts/linear/**/*.md` | Swap `@runner-brief.md` → compact brief |
| `automation/schemas/context_memory.schema.json` | JSON schema for compressor output |
| `automation/runners/context_compressor.py` | Ollama call, cache, `compact_job_context()` |
| `automation/runners/job_worker.py` | Call compressor in `render_prompt()`, wire stall retry |
| `automation/runners/cursor_stall.py` | Track + diagnose hung cursor-agent (exists, untracked) |
| `scripts/automation_compressor_doctor.py` | Smoke-test Ollama endpoint + schema validation |
| `tests/test_context_compressor.py` | Unit tests with mocked Ollama |
| `tests/test_job_worker_prompt.py` | Prompt render + task shrink tests |
| `docs/agent-automation.md` | Document compressor + token strategy |

---

### Task 1: Baseline verification gate

**Files:**
- Test: `tests/test_linear_router.py`

- [ ] **Step 1: Run router regression suite**

```bash
pytest tests/test_linear_router.py -q
```

Expected: `11 passed` (includes `test_router_committed_surface_uses_uuid_routing`).

- [ ] **Step 2: Confirm compressor disabled in local config**

Open `automation/config.yaml` — `context_compressor.enabled` must be `false` until Task 6 completes.

---

### Task 2: Shrink `build_job_payload` task string

**Files:**
- Modify: `automation/linear/router.py` (~397–401)
- Test: `tests/test_linear_router.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_linear_router.py`:

```python
def test_build_job_payload_task_is_compact():
    payload = {
        "action": "update",
        "type": "Issue",
        "updatedFrom": {"stateId": "49a46ce6-eb18-4377-95ae-b76f655a77b7"},
        "data": {
            "identifier": "NOV-38",
            "teamId": "97047174-6453-4458-b170-a9bf5f7b52e0",
            "projectId": "20965ebc-3ea7-4787-9310-f15ad9019007",
            "stateId": "0be134b7-bc56-4ba6-ba76-6b0a705e2ded",
            "labelIds": [],
        },
    }
    from automation.linear.router import build_job_payload, route_linear_webhook

    route = route_linear_webhook(payload, cfg=_TEST_CFG)
    assert route is not None
    job = build_job_payload(payload, route, cfg=_TEST_CFG)
    assert job["task"] == "NOV-38: status→In Progress"
    assert "Follow prompt" not in job["task"]
    assert len(job["task"]) < 80
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_linear_router.py::test_build_job_payload_task_is_compact -v
```

Expected: FAIL — task still contains `Follow prompt`.

- [ ] **Step 3: Implement minimal change**

In `automation/linear/router.py`, replace `build_job_payload` task block:

```python
    task = f"{identifier}: {route.reason}"
```

Remove unused `title` variable if nothing else references it.

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_linear_router.py::test_build_job_payload_task_is_compact -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add automation/linear/router.py tests/test_linear_router.py
git commit -m "refactor(automation): shrink Linear job task string for lower prompt tokens"
```

---

### Task 3: Add `runner-brief-compact.md`

**Files:**
- Create: `docs/agents/runner-brief-compact.md`

- [ ] **Step 1: Create compact brief**

Create `docs/agents/runner-brief-compact.md`:

```markdown
# Runner brief (compact)

Headless Linear jobs only. Full brief: `docs/agents/runner-brief.md`.

## Safety
- Repo only; one branch per job.
- No commit unless `commit: true` in prompt frontmatter.
- No merge to main without human approval.
- No destructive file moves without dry-run + approval.
- Smallest scoped verify; report command + exit code.
- New test **files** only when prompt says TEST_ALLOWED.

## Verify (default)
```bash
pytest <scoped> -v
python scripts/verify_phase_completion.py
cd web && npm run lint          # web touched
cd web && npm run test:contracts
```

## Output
Caveman mandatory for Linear reports and job stdout (see `.cursor/rules/caveman.mdc`).

## Job result
**status** · **changed paths** · **verification** · **blockers** · **next action**
```

- [ ] **Step 2: Commit**

```bash
git add docs/agents/runner-brief-compact.md
git commit -m "docs(automation): add compact runner brief for phase prompts"
```

---

### Task 4: Switch Linear phase prompts to compact brief

**Files:**
- Modify:
  - `automation/prompts/linear/backlog/create-research.md:11`
  - `automation/prompts/linear/backlog/grill-plan.md:11`
  - `automation/prompts/linear/todo/write-spec.md:11`
  - `automation/prompts/linear/todo/revise-spec.md:11`
  - `automation/prompts/linear/todo/defer-to-backlog.md:11`
  - `automation/prompts/linear/todo/write-todo-list.md:11`
  - `automation/prompts/linear/in-progress/implement.md:12`
  - `automation/prompts/linear/in-review/verify.md:12`

- [ ] **Step 1: Replace include line in all eight files**

Change:

```markdown
@docs/agents/runner-brief.md
```

To:

```markdown
@docs/agents/runner-brief-compact.md
```

- [ ] **Step 2: Add prompt size guard test**

Create `tests/test_prompt_templates.py`:

```python
"""Guardrail: phase prompts stay compact."""

from pathlib import Path

PROMPTS = Path(__file__).resolve().parents[1] / "automation" / "prompts" / "linear"


def test_linear_prompts_use_compact_runner_brief():
    offenders: list[str] = []
    for path in PROMPTS.rglob("*.md"):
        text = path.read_text(encoding="utf-8")
        if "@docs/agents/runner-brief.md" in text:
            offenders.append(str(path.relative_to(PROMPTS.parents[1])))
        assert "@docs/agents/runner-brief-compact.md" in text or path.parent.name == "archive"
    assert not offenders, f"Full runner-brief still referenced: {offenders}"


def test_linear_prompt_file_size_budget():
    for path in PROMPTS.rglob("*.md"):
        chars = len(path.read_text(encoding="utf-8"))
        assert chars < 3500, f"{path.name} too large ({chars} chars); target <3500 after compact brief"
```

- [ ] **Step 3: Run tests**

```bash
pytest tests/test_prompt_templates.py -v
```

Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add automation/prompts/linear docs/agents/runner-brief-compact.md tests/test_prompt_templates.py
git commit -m "refactor(automation): use compact runner brief in Linear phase prompts"
```

---

### Task 5: Context memory JSON schema

**Files:**
- Create: `automation/schemas/context_memory.schema.json`

- [ ] **Step 1: Create schema file**

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": [
    "goal",
    "current_phase",
    "locked_decisions",
    "must_keep_context",
    "changed_files",
    "relevant_tests",
    "risks",
    "unknowns",
    "discarded_noise",
    "next_prompt"
  ],
  "properties": {
    "goal": { "type": "string" },
    "current_phase": { "type": "string" },
    "locked_decisions": { "type": "array", "items": { "type": "string" } },
    "must_keep_context": { "type": "array", "items": { "type": "string" } },
    "changed_files": { "type": "array", "items": { "type": "string" } },
    "relevant_tests": { "type": "array", "items": { "type": "string" } },
    "risks": { "type": "array", "items": { "type": "string" } },
    "unknowns": { "type": "array", "items": { "type": "string" } },
    "discarded_noise": { "type": "array", "items": { "type": "string" } },
    "next_prompt": { "type": "string", "maxLength": 1200 }
  },
  "additionalProperties": false
}
```

- [ ] **Step 2: Commit**

```bash
git add automation/schemas/context_memory.schema.json
git commit -m "feat(automation): add context memory JSON schema for Ollama compressor"
```

---

### Task 6: Implement `context_compressor.py`

**Files:**
- Create: `automation/runners/context_compressor.py`
- Test: `tests/test_context_compressor.py`

- [ ] **Step 1: Write failing tests (mocked Ollama)**

Create `tests/test_context_compressor.py`:

```python
"""Tests for automation.runners.context_compressor."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from automation.runners.context_compressor import (
    compress_job_context,
    load_schema,
    memory_cache_path,
    source_hash,
)


def test_source_hash_stable():
    a = source_hash("hello")
    b = source_hash("hello")
    c = source_hash("world")
    assert a == b
    assert a != c


def test_load_schema_has_required_fields():
    schema = load_schema()
    assert "locked_decisions" in schema["properties"]


def test_compress_job_context_uses_cache(tmp_path: Path):
    cfg = {
        "context_compressor": {
            "enabled": True,
            "endpoint": "http://localhost:11434/api/generate",
            "model": "gemma4:latest",
            "cache_dir": str(tmp_path),
            "max_input_chars": 5000,
            "timeout_seconds": 30,
            "num_ctx": 8192,
            "top_p": 0.9,
        }
    }
    payload = {
        "id": "linear-NOV-38-in-progress-implement-x",
        "issue_identifier": "NOV-38",
        "prompt_file": "linear/in-progress/implement.md",
        "meta": {"route_reason": "status→In Progress"},
    }
    raw = "Issue NOV-38: implement bridge timeout table."
    fake_memory = {
        "goal": "Implement bridge timeouts",
        "current_phase": "implementation",
        "locked_decisions": ["[LOCK] No LibrarySession split"],
        "must_keep_context": [],
        "changed_files": ["web/src/bridgeTimeouts.ts"],
        "relevant_tests": ["web bridge contract tests"],
        "risks": [],
        "unknowns": [],
        "discarded_noise": ["greeting"],
        "next_prompt": "Implement bridgeTimeouts.ts per spec.",
    }

    with patch("automation.runners.context_compressor._ollama_generate_json", return_value=fake_memory):
        first = compress_job_context(cfg, payload=payload, raw_context=raw)
        second = compress_job_context(cfg, payload=payload, raw_context=raw)

    assert first["memory"] == fake_memory
    assert second["cached"] is True
    assert memory_cache_path(tmp_path, payload["id"]).is_file()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_context_compressor.py -v
```

Expected: FAIL — `ModuleNotFoundError: context_compressor`

- [ ] **Step 3: Implement `context_compressor.py`**

Create `automation/runners/context_compressor.py`:

```python
"""Compress job context via local Ollama before Cursor prompt delivery."""

from __future__ import annotations

import hashlib
import json
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from automation.runners.config import repo_root

_SCHEMA_PATH = (
    Path(__file__).resolve().parents[1] / "schemas" / "context_memory.schema.json"
)

_COMPRESSOR_PROMPT = """You are a strict context compressor for an automation coding pipeline.
Return ONLY valid JSON matching the schema fields.
Preserve locked_decisions and destructive-action warnings verbatim.
Do not invent files, labels, commits, test results, or status changes.
Remove boilerplate and progress chatter.
Keep next_prompt under 1200 characters.

Input:
{raw}
"""


def load_schema() -> dict[str, Any]:
    return json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))


def source_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _compressor_cfg(cfg: dict[str, Any]) -> dict[str, Any]:
    return cfg.get("context_compressor") or {}


def memory_cache_path(cache_dir: Path, job_id: str) -> Path:
    safe = job_id.replace("/", "_")
    return cache_dir / safe / "memory.json"


def _cache_dir(cfg: dict[str, Any]) -> Path:
    raw = _compressor_cfg(cfg).get("cache_dir") or "automation/context_cache"
    path = Path(raw)
    if not path.is_absolute():
        path = repo_root() / path
    path.mkdir(parents=True, exist_ok=True)
    return path


def _ollama_generate_json(*, endpoint: str, model: str, prompt: str, options: dict[str, Any], timeout: float) -> dict[str, Any]:
    body = json.dumps(
        {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": options,
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        endpoint,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return json.loads(data["response"])


def _validate_memory(memory: dict[str, Any]) -> None:
    schema = load_schema()
    required = schema.get("required") or []
    for key in required:
        if key not in memory:
            raise ValueError(f"context memory missing required key: {key}")
    if len(str(memory.get("next_prompt") or "")) > 1200:
        raise ValueError("next_prompt exceeds 1200 chars")


def compress_job_context(
    cfg: dict[str, Any],
    *,
    payload: dict[str, Any],
    raw_context: str,
) -> dict[str, Any]:
    comp = _compressor_cfg(cfg)
    if not comp.get("enabled"):
        return {"memory": None, "cached": False, "skipped": True}

    job_id = str(payload.get("id") or "unknown")
    cache_dir = _cache_dir(cfg)
    cache_file = memory_cache_path(cache_dir, job_id)
    digest = source_hash(raw_context)
    meta_file = cache_file.parent / "source_hash.txt"

    if cache_file.is_file() and meta_file.is_file() and meta_file.read_text(encoding="utf-8").strip() == digest:
        memory = json.loads(cache_file.read_text(encoding="utf-8"))
        return {"memory": memory, "cached": True, "source_hash": digest}

    clipped = raw_context[: int(comp.get("max_input_chars") or 12000)]
    prompt = _COMPRESSOR_PROMPT.format(raw=clipped)
    options = {
        "temperature": 0,
        "num_ctx": int(comp.get("num_ctx") or 32768),
        "top_p": float(comp.get("top_p") or 0.9),
    }
    memory = _ollama_generate_json(
        endpoint=str(comp.get("endpoint") or "http://localhost:11434/api/generate"),
        model=str(comp.get("model") or "gemma4:latest"),
        prompt=prompt,
        options=options,
        timeout=float(comp.get("timeout_seconds") or 180),
    )
    _validate_memory(memory)

    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(json.dumps(memory, ensure_ascii=False, indent=2), encoding="utf-8")
    meta_file.write_text(digest + "\n", encoding="utf-8")

    ratio = len(json.dumps(memory)) / max(1, len(clipped))
    return {
        "memory": memory,
        "cached": False,
        "source_hash": digest,
        "compression_ratio": ratio,
    }
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_context_compressor.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add automation/runners/context_compressor.py tests/test_context_compressor.py automation/schemas/context_memory.schema.json
git commit -m "feat(automation): add Ollama context compressor with source-hash cache"
```

---

### Task 7: Wire compressor into `render_prompt()`

**Files:**
- Modify: `automation/runners/job_worker.py:146-176`
- Test: `tests/test_job_worker_prompt.py`

- [ ] **Step 1: Write failing test**

Create `tests/test_job_worker_prompt.py`:

```python
from __future__ import annotations

from unittest.mock import patch

from automation.runners.job_worker import render_prompt


def test_render_prompt_injects_context_memory_when_enabled(tmp_path):
    cfg = {
        "prompts": {"dir": "automation/prompts"},
        "context_compressor": {"enabled": True, "cache_dir": str(tmp_path)},
    }
    payload = {
        "id": "linear-NOV-38-test",
        "repo": "novelguard",
        "kind": "linear",
        "task": "NOV-38: status→In Progress",
        "prompt_file": "linear/in-progress/implement.md",
        "issue_identifier": "NOV-38",
        "issue_url": "https://linear.app/example/NOV-38",
        "linear_state": "In Progress",
        "meta": {"route_reason": "status→In Progress", "linear_event": {}},
    }
    fake_memory = {
        "goal": "g",
        "current_phase": "implementation",
        "locked_decisions": [],
        "must_keep_context": [],
        "changed_files": [],
        "relevant_tests": [],
        "risks": [],
        "unknowns": [],
        "discarded_noise": [],
        "next_prompt": "Do the thing.",
    }
    with patch(
        "automation.runners.job_worker.compress_job_context",
        return_value={"memory": fake_memory, "cached": False},
    ):
        rendered = render_prompt(cfg, payload, branch="ai/job-test")

    assert "{{CONTEXT_MEMORY_JSON}}" not in rendered
    assert '"next_prompt": "Do the thing."' in rendered or "Do the thing." in rendered
```

Add placeholder to `automation/prompts/linear/in-progress/implement.md` before `## Gate`:

```markdown
## Context memory
{{CONTEXT_MEMORY_JSON}}
```

- [ ] **Step 2: Run test — expect FAIL**

```bash
pytest tests/test_job_worker_prompt.py -v
```

- [ ] **Step 3: Implement in `render_prompt()`**

At top of `job_worker.py` add import:

```python
from automation.runners.context_compressor import compress_job_context
```

Inside `render_prompt()`, before building `replacements`:

```python
    raw_context = "\n".join(
        [
            str(payload.get("task") or ""),
            str(meta.get("route_reason") or ""),
            json.dumps(linear_event or {}, ensure_ascii=False),
        ]
    )
    memory_result = compress_job_context(cfg, payload=payload, raw_context=raw_context)
    memory = memory_result.get("memory")
    memory_json = json.dumps(memory, ensure_ascii=False, indent=2) if memory else "{}"
```

Add to `replacements`:

```python
        "{{CONTEXT_MEMORY_JSON}}": memory_json,
        "{{NEXT_PROMPT}}": str((memory or {}).get("next_prompt") or payload.get("task") or ""),
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_job_worker_prompt.py tests/test_context_compressor.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add automation/runners/job_worker.py automation/prompts/linear/in-progress/implement.md tests/test_job_worker_prompt.py
git commit -m "feat(automation): inject Ollama context memory into rendered prompts"
```

---

### Task 8: Add `{{CONTEXT_MEMORY_JSON}}` to remaining phase prompts

**Files:**
- Modify all `automation/prompts/linear/**/*.md` except archive

- [ ] **Step 1: Add section after frontmatter to each phase prompt**

```markdown
## Context memory
{{CONTEXT_MEMORY_JSON}}
```

- [ ] **Step 2: Run prompt template tests**

```bash
pytest tests/test_prompt_templates.py tests/test_job_worker_prompt.py -v
```

- [ ] **Step 3: Commit**

```bash
git add automation/prompts/linear
git commit -m "chore(automation): add context memory placeholder to Linear prompts"
```

---

### Task 9: Wire `cursor_stall.py` into `process_job()`

**Files:**
- Modify: `automation/runners/job_worker.py` (streaming path ~356–390)
- Add: `automation/runners/cursor_stall.py` to git (already on disk)
- Test: extend `tests/test_automation_tui.py` or new `tests/test_cursor_stall_worker.py`

- [ ] **Step 1: Write failing stall retry test**

Create `tests/test_cursor_stall_worker.py`:

```python
from unittest.mock import MagicMock, patch

from automation.runners.cursor_stall import CursorOutputTracker, cursor_stall_config


def test_cursor_stall_config_defaults():
    stall, retries, poll = cursor_stall_config({"cursor": {}})
    assert stall == 300.0
    assert retries == 1
    assert poll == 5.0


def test_output_tracker_idle_seconds():
    t0 = 1000.0
    tracker = CursorOutputTracker(now=t0)
    assert tracker.idle_seconds(now=t0 + 10) == 10.0
```

- [ ] **Step 2: Run — expect PASS if cursor_stall already correct**

```bash
pytest tests/test_cursor_stall_worker.py -v
```

- [ ] **Step 3: Integrate stall tracker in streaming `on_line`**

In `process_job()` TUI streaming branch, replace ad-hoc `last_line_at` monitor with:

```python
from automation.runners.cursor_stall import (
    CursorOutputTracker,
    cursor_stall_config,
    diagnose_cursor_stall,
    write_stall_diagnosis,
)

stall_seconds, stall_max_retries, stall_poll = cursor_stall_config(cfg)
tracker = CursorOutputTracker()

def on_line(stream: str, line: str) -> None:
    tracker.note_line(stream, line)
    ...
```

Wrap `run_prompt_streaming` in retry loop (max `stall_max_retries`). On idle ≥ `stall_seconds` while proc running: `write_stall_diagnosis`, `request_cancel()`, retry.

- [ ] **Step 4: Commit tracked stall module**

```bash
git add automation/runners/cursor_stall.py automation/runners/job_worker.py tests/test_cursor_stall_worker.py
git commit -m "feat(automation): wire cursor stall detection and retry into job worker"
```

---

### Task 10: Compressor doctor script + config example

**Files:**
- Create: `scripts/automation_compressor_doctor.py`
- Modify: `automation/config.example.yaml`

- [ ] **Step 1: Create doctor script**

```python
#!/usr/bin/env python3
"""Smoke-test Ollama context compressor."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from automation.runners.config import load_config
from automation.runners.context_compressor import compress_job_context


def main() -> int:
    cfg = load_config()
    comp = cfg.get("context_compressor") or {}
    if not comp.get("enabled"):
        print("context_compressor.enabled is false — enable to test")
        return 0
    payload = {
        "id": "doctor-smoke",
        "issue_identifier": "NOV-0",
        "prompt_file": "linear/in-progress/implement.md",
        "meta": {"route_reason": "doctor"},
    }
    raw = "Doctor smoke: preserve [LOCK] demo decision."
    result = compress_job_context(cfg, payload=payload, raw_context=raw)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result.get("memory") else 1


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Add `context_compressor` block to `automation/config.example.yaml`**

Mirror fields from `automation/config.yaml` (`enabled: false` default).

- [ ] **Step 3: Manual doctor run (Ollama must be up)**

```bash
# temporarily set context_compressor.enabled: true in automation/config.yaml
python scripts/automation_compressor_doctor.py
```

Expected: JSON with `memory.goal` and `locked_decisions` containing `[LOCK] demo decision`.

- [ ] **Step 4: Commit**

```bash
git add scripts/automation_compressor_doctor.py automation/config.example.yaml
git commit -m "chore(automation): add Ollama compressor doctor script"
```

---

### Task 11: Documentation update

**Files:**
- Modify: `docs/agent-automation.md`

- [ ] **Step 1: Add sections**

Under Linear webhook routing, append:

```markdown
### Token / context pipeline

1. **Router (Python)** picks one `linear/*` prompt — never `archive/01-linear-status-changed-router.md`.
2. **Phase prompts** use `runner-brief-compact.md` (~40 lines).
3. **Optional compressor** (`context_compressor.enabled: true`): gemma4:latest summarizes prior context into `automation/context_cache/<job-id>/memory.json`. Fail closed — if compression fails, job aborts (no raw dump fallback).
4. **Stall guard**: `cursor.stall_seconds` (default 300) cancels hung cursor-agent and retries once.

Doctor: `python scripts/automation_compressor_doctor.py`
```

- [ ] **Step 2: Commit**

```bash
git add docs/agent-automation.md
git commit -m "docs(automation): document token pipeline and Ollama compressor"
```

---

### Task 12: Final verification

- [ ] **Step 1: Compile check**

```bash
python -m compileall automation/linear automation/runners scripts/automation_daemon.py scripts/automation_compressor_doctor.py
```

Expected: exit 0

- [ ] **Step 2: Test suite**

```bash
pytest tests/test_linear_router.py tests/test_prompt_templates.py tests/test_context_compressor.py tests/test_job_worker_prompt.py tests/test_cursor_stall_worker.py tests/test_automation_tui.py -q
```

Expected: all pass

- [ ] **Step 3: Dry-run webhook route smoke**

```bash
python scripts/linear_webhook_handler.py test --fixture automation/examples/linear-webhook-issue-stateid-only.json
```

Expected: `"status": "queued"`

- [ ] **Step 4: Restart daemon after merge**

```bash
python scripts/automation_daemon.py
```

---

## Self-review

| Spec requirement | Task |
|------------------|------|
| Python router decides phase (not AI router prompt) | Baseline `e7e466a` — no change |
| Phase prompt split / no 01-router | Already `linear/*`; Task 4 compacts |
| Ollama gemma4 compressor | Tasks 5–7, 10 |
| No raw history fallback on compress fail | Task 6 `_validate_memory` + abort in Task 7 |
| cursor stall 300s retry | Task 9 |
| task string shrink | Task 2 |
| daemon queue reuse | Already in `automation_daemon.py` — no task |
| webhook pre-enqueue stats removed | Already done — no task |

**Placeholder scan:** none.

---

## Execution handoff

Plan saved to `docs/superpowers/plans/2026-06-05-automation-token-pipeline-optimization.md`.

**Two execution options:**

1. **Subagent-Driven (recommended)** — fresh subagent per task, review between tasks, fast iteration
2. **Inline Execution** — run tasks in this session with executing-plans checkpoints

Which approach?
