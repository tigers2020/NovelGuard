# Automation Cycle Smoke Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a B-depth prompt-pipeline smoke harness that walks ~12 UUID webhook fixtures through `route_linear_webhook` → `build_job_payload` → `render_prompt`, covering two parent routing trees and a combined state+label regression case.

**Architecture:** Core logic in `automation/runners/cycle_smoke.py` (importable, no queue/cursor side effects). Fixtures + manifest under `automation/examples/cycle-smoke/`. CLI at `scripts/automation_cycle_smoke.py`. Default compressor mock; `--live-compressor` for Ollama. Spec: `docs/superpowers/specs/2026-06-05-automation-cycle-smoke-design.md`.

**Tech Stack:** Python 3.12, pytest, `automation/linear/router.py`, `automation/runners/job_worker.py`, optional Ollama via existing `context_compressor`.

---

## File map

| File | Responsibility |
|------|----------------|
| `automation/runners/cycle_smoke.py` | Load manifest, run cases, validate route/payload/render |
| `scripts/automation_cycle_smoke.py` | CLI entrypoint |
| `automation/examples/cycle-smoke/manifest.json` | Groups + case metadata |
| `automation/examples/cycle-smoke/*.json` | Webhook fixture payloads |
| `tests/test_cycle_smoke.py` | CI-safe pytest over manifest (mock compressor) |
| `docs/agent-automation.md` | Document smoke command |

---

### Task 0: Commit pending compressor coerce fix (prerequisite)

**Files:**
- Modify: `automation/runners/context_compressor.py`
- Modify: `scripts/automation_compressor_doctor.py`
- Modify: `tests/test_context_compressor.py`

- [ ] **Step 1: Verify compressor tests pass**

```bash
pytest tests/test_context_compressor.py -q
```

Expected: `6 passed` (includes `test_coerce_memory_fills_missing_required_keys`).

- [ ] **Step 2: Verify doctor against live Ollama (optional)**

```bash
python scripts/automation_compressor_doctor.py
```

Expected: exit `0`, JSON with `memory.goal` set.

- [ ] **Step 3: Commit**

```bash
git add automation/runners/context_compressor.py scripts/automation_compressor_doctor.py tests/test_context_compressor.py
git commit -m "fix(automation): coerce partial Ollama context memory to required schema"
```

---

### Task 1: Manifest + fixture directory

**Files:**
- Create: `automation/examples/cycle-smoke/manifest.json`
- Create: `automation/examples/cycle-smoke/_base-issue.json` (shared fields reference only — optional inline in each fixture)

- [ ] **Step 1: Create manifest**

Create `automation/examples/cycle-smoke/manifest.json`:

```json
{
  "issue": "NOV-SMOKE",
  "default_max_chars": 24000,
  "groups": [
    {
      "id": "state_changed",
      "cases": [
        {
          "id": "A3-in-progress",
          "fixture": "A3-in-progress.json",
          "expect_prompt": "linear/in-progress/implement.md",
          "expect_reason_contains": "status→In Progress"
        },
        {
          "id": "A4-pure-in-review",
          "fixture": "A4-pure-in-review.json",
          "expect_prompt": "linear/in-review/verify.md",
          "expect_reason_contains": "status→In Review"
        },
        {
          "id": "A-combined-in-review-impl-done",
          "fixture": "A-combined-in-review-impl-done.json",
          "expect_prompt": "linear/in-review/verify.md",
          "expect_reason_contains": "impl-done→verify"
        },
        {
          "id": "A1-in-progress-impl-done",
          "fixture": "A1-in-progress-impl-done.json",
          "expect_prompt": "linear/in-review/verify.md",
          "expect_reason_contains": "impl-done→verify"
        }
      ]
    },
    {
      "id": "labels_only",
      "cases": [
        {
          "id": "B3-impl-done-diff",
          "fixture": "B3-impl-done-diff.json",
          "expect_prompt": "linear/in-review/verify.md",
          "expect_reason_contains": "impl-done→verify"
        },
        {
          "id": "B1-todo-list-done",
          "fixture": "B1-todo-list-done.json",
          "expect_prompt": "linear/in-progress/implement.md",
          "expect_reason_contains": "todo-list-done→implement"
        },
        {
          "id": "B2-plan-done",
          "fixture": "B2-plan-done.json",
          "expect_prompt": "linear/todo/write-todo-list.md"
        },
        {
          "id": "B2-research-done",
          "fixture": "B2-research-done.json",
          "expect_prompt": "linear/todo/write-spec.md"
        },
        {
          "id": "B-backlog-spec-done",
          "fixture": "B-backlog-spec-done.json",
          "expect_prompt": "linear/backlog/grill-plan.md"
        }
      ]
    },
    {
      "id": "terminal",
      "cases": [
        {
          "id": "ignore-verify-done",
          "fixture": "ignore-verify-done.json",
          "expect_route": null
        },
        {
          "id": "ignore-done-status",
          "fixture": "ignore-done-status.json",
          "expect_route": null
        }
      ]
    }
  ]
}
```

- [ ] **Step 2: Commit manifest skeleton**

```bash
git add automation/examples/cycle-smoke/manifest.json
git commit -m "chore(automation): add cycle-smoke manifest skeleton"
```

---

### Task 2: Webhook fixtures (UUID production shape)

**Files:**
- Create: `automation/examples/cycle-smoke/A3-in-progress.json`
- Create: `automation/examples/cycle-smoke/A4-pure-in-review.json`
- Create: `automation/examples/cycle-smoke/A-combined-in-review-impl-done.json`
- Create: `automation/examples/cycle-smoke/A1-in-progress-impl-done.json`
- Create: `automation/examples/cycle-smoke/B3-impl-done-diff.json`
- Create: `automation/examples/cycle-smoke/B1-todo-list-done.json`
- Create: `automation/examples/cycle-smoke/B2-plan-done.json`
- Create: `automation/examples/cycle-smoke/B2-research-done.json`
- Create: `automation/examples/cycle-smoke/B-backlog-spec-done.json`
- Create: `automation/examples/cycle-smoke/ignore-verify-done.json`
- Create: `automation/examples/cycle-smoke/ignore-done-status.json`

Use UUIDs from `automation/linear/linear_ids.py` (`DEFAULT_STATE_IDS`, `DEFAULT_LABEL_IDS`). Every `data` block includes `teamId` + `projectId` for scope.

- [ ] **Step 1: Create `A3-in-progress.json`**

```json
{
  "action": "update",
  "type": "Issue",
  "webhookId": "smoke-a3",
  "updatedFrom": {
    "stateId": "49a46ce6-eb18-4377-95ae-b76f655a77b7"
  },
  "data": {
    "identifier": "NOV-SMOKE",
    "url": "https://linear.app/example/issue/NOV-SMOKE",
    "teamId": "97047174-6453-4458-b170-a9bf5f7b52e0",
    "projectId": "20965ebc-3ea7-4787-9310-f15ad9019007",
    "stateId": "0be134b7-bc56-4ba6-ba76-6b0a705e2ded",
    "labelIds": []
  }
}
```

- [ ] **Step 2: Create `A4-pure-in-review.json`**

```json
{
  "action": "update",
  "type": "Issue",
  "webhookId": "smoke-a4",
  "updatedFrom": {
    "stateId": "0be134b7-bc56-4ba6-ba76-6b0a705e2ded"
  },
  "data": {
    "identifier": "NOV-SMOKE",
    "url": "https://linear.app/example/issue/NOV-SMOKE",
    "teamId": "97047174-6453-4458-b170-a9bf5f7b52e0",
    "projectId": "20965ebc-3ea7-4787-9310-f15ad9019007",
    "stateId": "31a91042-9d59-49eb-8821-43ddd92ed76d",
    "labelIds": ["75d4a692-8214-4592-8f45-f29f93162b45"]
  }
}
```

- [ ] **Step 3: Create `A-combined-in-review-impl-done.json`**

```json
{
  "action": "update",
  "type": "Issue",
  "webhookId": "smoke-a-combined",
  "updatedFrom": {
    "stateId": "0be134b7-bc56-4ba6-ba76-6b0a705e2ded",
    "labelIds": ["75d4a692-8214-4592-8f45-f29f93162b45"]
  },
  "data": {
    "identifier": "NOV-SMOKE",
    "url": "https://linear.app/example/issue/NOV-SMOKE",
    "teamId": "97047174-6453-4458-b170-a9bf5f7b52e0",
    "projectId": "20965ebc-3ea7-4787-9310-f15ad9019007",
    "stateId": "31a91042-9d59-49eb-8821-43ddd92ed76d",
    "labelIds": [
      "75d4a692-8214-4592-8f45-f29f93162b45",
      "41269879-fa85-478c-bca6-3329340d8069"
    ]
  }
}
```

- [ ] **Step 4: Create `A1-in-progress-impl-done.json`**

```json
{
  "action": "update",
  "type": "Issue",
  "webhookId": "smoke-a1",
  "updatedFrom": {
    "stateId": "49a46ce6-eb18-4377-95ae-b76f655a77b7"
  },
  "data": {
    "identifier": "NOV-SMOKE",
    "url": "https://linear.app/example/issue/NOV-SMOKE",
    "teamId": "97047174-6453-4458-b170-a9bf5f7b52e0",
    "projectId": "20965ebc-3ea7-4787-9310-f15ad9019007",
    "stateId": "0be134b7-bc56-4ba6-ba76-6b0a705e2ded",
    "labelIds": ["41269879-fa85-478c-bca6-3329340d8069"]
  }
}
```

- [ ] **Step 5: Create `B3-impl-done-diff.json`**

```json
{
  "action": "update",
  "type": "Issue",
  "webhookId": "smoke-b3",
  "updatedFrom": {
    "labelIds": ["75d4a692-8214-4592-8f45-f29f93162b45"]
  },
  "data": {
    "identifier": "NOV-SMOKE",
    "url": "https://linear.app/example/issue/NOV-SMOKE",
    "teamId": "97047174-6453-4458-b170-a9bf5f7b52e0",
    "projectId": "20965ebc-3ea7-4787-9310-f15ad9019007",
    "stateId": "0be134b7-bc56-4ba6-ba76-6b0a705e2ded",
    "labelIds": [
      "75d4a692-8214-4592-8f45-f29f93162b45",
      "41269879-fa85-478c-bca6-3329340d8069"
    ]
  }
}
```

- [ ] **Step 6: Create `B1-todo-list-done.json`**

```json
{
  "action": "update",
  "type": "Issue",
  "webhookId": "smoke-b1",
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
      "75d4a692-8214-4592-8f45-f29f93162b45"
    ]
  }
}
```

- [ ] **Step 7: Create `B2-plan-done.json`**

```json
{
  "action": "update",
  "type": "Issue",
  "webhookId": "smoke-b2-plan",
  "updatedFrom": {
    "labelIds": ["bffa5b70-6009-4c1c-8f6a-f7fd62e79621"]
  },
  "data": {
    "identifier": "NOV-SMOKE",
    "url": "https://linear.app/example/issue/NOV-SMOKE",
    "teamId": "97047174-6453-4458-b170-a9bf5f7b52e0",
    "projectId": "20965ebc-3ea7-4787-9310-f15ad9019007",
    "stateId": "49a46ce6-eb18-4377-95ae-b76f655a77b7",
    "labelIds": [
      "bffa5b70-6009-4c1c-8f6a-f7fd62e79621",
      "f3424dcd-6d2c-47f9-a8fe-5f4d5b626d27"
    ]
  }
}
```

- [ ] **Step 8: Create `B2-research-done.json`**

```json
{
  "action": "update",
  "type": "Issue",
  "webhookId": "smoke-b2-research",
  "updatedFrom": {
    "labelIds": []
  },
  "data": {
    "identifier": "NOV-SMOKE",
    "url": "https://linear.app/example/issue/NOV-SMOKE",
    "teamId": "97047174-6453-4458-b170-a9bf5f7b52e0",
    "projectId": "20965ebc-3ea7-4787-9310-f15ad9019007",
    "stateId": "49a46ce6-eb18-4377-95ae-b76f655a77b7",
    "labelIds": ["b26a0e92-112f-49dc-bdc1-16628995c020"]
  }
}
```

- [ ] **Step 9: Create `B-backlog-spec-done.json`**

```json
{
  "action": "update",
  "type": "Issue",
  "webhookId": "smoke-b-grill",
  "updatedFrom": {
    "labelIds": []
  },
  "data": {
    "identifier": "NOV-SMOKE",
    "url": "https://linear.app/example/issue/NOV-SMOKE",
    "teamId": "97047174-6453-4458-b170-a9bf5f7b52e0",
    "projectId": "20965ebc-3ea7-4787-9310-f15ad9019007",
    "stateId": "180fc254-f066-4fad-a425-7ebab180d4c6",
    "labelIds": ["bffa5b70-6009-4c1c-8f6a-f7fd62e79621"]
  }
}
```

- [ ] **Step 10: Create `ignore-verify-done.json`**

```json
{
  "action": "update",
  "type": "Issue",
  "webhookId": "smoke-ignore-verify",
  "updatedFrom": {
    "labelIds": ["41269879-fa85-478c-bca6-3329340d8069"]
  },
  "data": {
    "identifier": "NOV-SMOKE",
    "teamId": "97047174-6453-4458-b170-a9bf5f7b52e0",
    "projectId": "20965ebc-3ea7-4787-9310-f15ad9019007",
    "stateId": "31a91042-9d59-49eb-8821-43ddd92ed76d",
    "labelIds": [
      "41269879-fa85-478c-bca6-3329340d8069",
      "65836882-f344-4675-b3a2-552a3fb3c79c"
    ]
  }
}
```

- [ ] **Step 11: Create `ignore-done-status.json`**

```json
{
  "action": "update",
  "type": "Issue",
  "webhookId": "smoke-ignore-done",
  "updatedFrom": {
    "stateId": "31a91042-9d59-49eb-8821-43ddd92ed76d"
  },
  "data": {
    "identifier": "NOV-SMOKE",
    "teamId": "97047174-6453-4458-b170-a9bf5f7b52e0",
    "projectId": "20965ebc-3ea7-4787-9310-f15ad9019007",
    "stateId": "537a17f3-7fe0-46f0-94d3-89f36f48e98c",
    "labelIds": [
      "41269879-fa85-478c-bca6-3329340d8069",
      "65836882-f344-4675-b3a2-552a3fb3c79c"
    ]
  }
}
```

- [ ] **Step 12: Sanity-check fixtures against router**

```bash
python -c "
import json
from pathlib import Path
from automation.linear.router import route_linear_webhook
from automation.runners.config import load_config
cfg = load_config()
root = Path('automation/examples/cycle-smoke')
for p in sorted(root.glob('*.json')):
    if p.name == 'manifest.json':
        continue
    r = route_linear_webhook(json.loads(p.read_text()), cfg=cfg)
    print(p.name, '->', r.prompt_file if r else None, r.reason if r else 'ignored')
"
```

Expected: each fixture routes as manifest expects (fix fixture `updatedFrom` if any mismatch).

- [ ] **Step 13: Commit fixtures**

```bash
git add automation/examples/cycle-smoke/*.json
git commit -m "test(automation): add cycle-smoke UUID webhook fixtures"
```

---

### Task 3: `cycle_smoke.py` — route validation

**Files:**
- Create: `automation/runners/cycle_smoke.py`
- Test: `tests/test_cycle_smoke.py`

- [ ] **Step 1: Write failing test (route only)**

Create `tests/test_cycle_smoke.py`:

```python
"""CI-safe automation cycle smoke (mock compressor)."""

from __future__ import annotations

from automation.runners.cycle_smoke import load_manifest, run_case, run_manifest


def test_load_manifest_has_twelve_cases():
    manifest = load_manifest()
    cases = [c for g in manifest["groups"] for c in g["cases"]]
    assert len(cases) == 11


def test_A_combined_routes_impl_done_over_status():
    manifest = load_manifest()
    case = next(
        c
        for g in manifest["groups"]
        for c in g["cases"]
        if c["id"] == "A-combined-in-review-impl-done"
    )
    result = run_case(case, live_compressor=False, render=False)
    assert result.ok, result.errors
    assert result.prompt_file == "linear/in-review/verify.md"
    assert result.route_reason and "impl-done→verify" in result.route_reason
```

- [ ] **Step 2: Run test — expect FAIL**

```bash
ALLOW_NEW_TESTS=1 pytest tests/test_cycle_smoke.py::test_load_manifest_has_twelve_cases -v
```

Expected: FAIL — `cycle_smoke` module not found.

- [ ] **Step 3: Implement `cycle_smoke.py` (route stage)**

Create `automation/runners/cycle_smoke.py`:

```python
"""Prompt-pipeline smoke: route → payload → render (no queue/cursor)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from automation.linear.router import build_job_payload, route_linear_webhook
from automation.runners.config import load_config, repo_root

_MANIFEST = repo_root() / "automation" / "examples" / "cycle-smoke" / "manifest.json"
_FIXTURES = _MANIFEST.parent

_WORKER_PLACEHOLDERS = (
    "{{TASK}}",
    "{{JOB_ID}}",
    "{{BRANCH}}",
    "{{ISSUE_IDENTIFIER}}",
    "{{ISSUE_URL}}",
    "{{ROUTE_REASON}}",
    "{{LINEAR_STATE}}",
    "{{LINEAR_EVENT}}",
    "{{CONTEXT_MEMORY_JSON}}",
    "{{NEXT_PROMPT}}",
)

_MOCK_MEMORY: dict[str, Any] = {
    "goal": "NOV-SMOKE cycle smoke",
    "current_phase": "smoke",
    "locked_decisions": ["[LOCK] smoke fixture"],
    "must_keep_context": [],
    "changed_files": [],
    "relevant_tests": [],
    "risks": [],
    "unknowns": [],
    "discarded_noise": [],
    "next_prompt": "Continue smoke case.",
}


@dataclass
class CaseResult:
    case_id: str
    group_id: str
    ok: bool
    prompt_file: str | None = None
    route_reason: str | None = None
    rendered_chars: int = 0
    errors: list[str] = field(default_factory=list)


def load_manifest(path: Path | None = None) -> dict[str, Any]:
    p = path or _MANIFEST
    return json.loads(p.read_text(encoding="utf-8"))


def _load_fixture(name: str) -> dict[str, Any]:
    return json.loads((_FIXTURES / name).read_text(encoding="utf-8"))


def _validate_route(case: dict[str, Any], route) -> list[str]:
    errors: list[str] = []
    expect_null = case.get("expect_route") is None and "expect_prompt" not in case
    if expect_null or case.get("expect_route") is None and case.get("expect_prompt") is None:
        if route is not None:
            errors.append(f"expected no route, got {route.prompt_file}")
        return errors
    if route is None:
        errors.append("expected route, got None")
        return errors
    expect_prompt = case.get("expect_prompt")
    if expect_prompt and route.prompt_file != expect_prompt:
        errors.append(f"prompt_file {route.prompt_file!r} != {expect_prompt!r}")
    substr = case.get("expect_reason_contains")
    if substr and substr not in route.reason:
        errors.append(f"route.reason {route.reason!r} missing {substr!r}")
    return errors


def run_case(
    case: dict[str, Any],
    *,
    group_id: str = "",
    cfg: dict[str, Any] | None = None,
    live_compressor: bool = False,
    render: bool = True,
) -> CaseResult:
    cfg = cfg or load_config()
    case_id = str(case["id"])
    payload = _load_fixture(str(case["fixture"]))
    route = route_linear_webhook(payload, cfg=cfg)
    errors = _validate_route(case, route)
    prompt_file = route.prompt_file if route else None
    route_reason = route.reason if route else None

    if render and route is not None and not errors:
        errors.extend(_validate_render(case, cfg, payload, route, live_compressor=live_compressor))

    return CaseResult(
        case_id=case_id,
        group_id=group_id,
        ok=not errors,
        prompt_file=prompt_file,
        route_reason=route_reason,
        errors=errors,
    )


def _validate_render(
    case: dict[str, Any],
    cfg: dict[str, Any],
    webhook_payload: dict[str, Any],
    route,
    *,
    live_compressor: bool,
) -> list[str]:
    from unittest.mock import patch

    from automation.runners.job_worker import render_prompt

    errors: list[str] = []
    job = build_job_payload(webhook_payload, route, cfg=cfg)
    branch = f"ai/cycle-smoke-{case['id']}"

    if live_compressor:
        rendered = render_prompt(cfg, job, branch)
    else:
        with patch(
            "automation.runners.job_worker.compress_job_context",
            return_value={"memory": dict(_MOCK_MEMORY), "cached": False},
        ):
            rendered = render_prompt(cfg, job, branch)

    for ph in _WORKER_PLACEHOLDERS:
        if ph in rendered:
            errors.append(f"unresolved placeholder {ph}")

    if "@docs/agents/runner-brief.md" in rendered and "runner-brief-compact" not in rendered:
        errors.append("full runner-brief.md referenced")

    if "runner-brief-compact" not in rendered:
        errors.append("runner-brief-compact not referenced")

    mem_match = re.search(
        r"## Context memory\s*\n(\{.*?\n\})",
        rendered,
        re.DOTALL,
    )
    if not mem_match:
        errors.append("missing Context memory JSON block")
    else:
        try:
            json.loads(mem_match.group(1))
        except json.JSONDecodeError as exc:
            errors.append(f"invalid context memory JSON: {exc}")

    max_chars = int(case.get("max_chars") or 24000)
    if len(rendered) > max_chars:
        errors.append(f"rendered length {len(rendered)} > {max_chars}")

    return errors


def run_manifest(
    *,
    group: str | None = None,
    live_compressor: bool = False,
    stop_on_fail: bool = True,
    cfg: dict[str, Any] | None = None,
) -> list[CaseResult]:
    manifest = load_manifest()
    cfg = cfg or load_config()
    results: list[CaseResult] = []
    for grp in manifest["groups"]:
        gid = str(grp["id"])
        if group and gid != group:
            continue
        for case in grp["cases"]:
            result = run_case(
                case,
                group_id=gid,
                cfg=cfg,
                live_compressor=live_compressor,
                render=True,
            )
            results.append(result)
            if not result.ok and stop_on_fail:
                return results
    return results
```

- [ ] **Step 4: Run tests**

```bash
ALLOW_NEW_TESTS=1 pytest tests/test_cycle_smoke.py -v
```

Expected: PASS (both tests).

- [ ] **Step 5: Commit**

```bash
ALLOW_NEW_TESTS=1 git add automation/runners/cycle_smoke.py tests/test_cycle_smoke.py
git commit -m "feat(automation): add cycle smoke runner for route and render pipeline"
```

---

### Task 4: CLI script

**Files:**
- Create: `scripts/automation_cycle_smoke.py`

- [ ] **Step 1: Create CLI**

```python
#!/usr/bin/env python3
"""B-depth automation cycle smoke: route → payload → render_prompt."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from automation.runners.cycle_smoke import run_manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Automation cycle smoke (prompt pipeline)")
    parser.add_argument("--group", help="Run only one manifest group id")
    parser.add_argument("--live-compressor", action="store_true", help="Use real Ollama")
    parser.add_argument("--all", action="store_true", help="Run all cases even after failures")
    args = parser.parse_args()

    results = run_manifest(
        group=args.group,
        live_compressor=args.live_compressor,
        stop_on_fail=not args.all,
    )
    for r in results:
        status = "PASS" if r.ok else "FAIL"
        line = f"[{status}] {r.group_id}/{r.case_id}"
        if r.prompt_file:
            line += f" → {r.prompt_file}"
        print(line)
        for err in r.errors:
            print(f"  ! {err}", file=sys.stderr)

    summary = {
        "passed": sum(1 for r in results if r.ok),
        "failed": sum(1 for r in results if not r.ok),
        "total": len(results),
    }
    print(json.dumps(summary, indent=2))
    failed = summary["failed"]
    if failed and not args.all:
        return 1
    if args.all and failed:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Run CLI**

```bash
python scripts/automation_cycle_smoke.py
```

Expected: `11` cases PASS, exit `0`.

- [ ] **Step 3: Run combined regression explicitly**

```bash
python scripts/automation_cycle_smoke.py --group state_changed
```

Expected: `A-combined-in-review-impl-done` PASS with `impl-done→verify`.

- [ ] **Step 4: Commit**

```bash
git add scripts/automation_cycle_smoke.py
git commit -m "feat(automation): add automation_cycle_smoke CLI"
```

---

### Task 5: Full manifest pytest + live compressor optional test

**Files:**
- Modify: `tests/test_cycle_smoke.py`

- [ ] **Step 1: Add full manifest test**

Append to `tests/test_cycle_smoke.py`:

```python
def test_full_manifest_mock_compressor():
    results = run_manifest(live_compressor=False, stop_on_fail=False)
    failed = [r for r in results if not r.ok]
    assert len(results) == 11
    assert not failed, failed[0].errors if failed else []
```

- [ ] **Step 2: Run**

```bash
ALLOW_NEW_TESTS=1 pytest tests/test_cycle_smoke.py -q
```

Expected: `3 passed`.

- [ ] **Step 3: Optional live Ollama (manual)**

```bash
python scripts/automation_cycle_smoke.py --live-compressor --group state_changed
```

Expected: exit `0` when Ollama up and `context_compressor.enabled: true`.

- [ ] **Step 4: Commit**

```bash
git add tests/test_cycle_smoke.py
git commit -m "test(automation): full cycle smoke manifest coverage"
```

---

### Task 6: Documentation

**Files:**
- Modify: `docs/agent-automation.md`

- [ ] **Step 1: Add subsection after Token / context pipeline**

```markdown
### Cycle smoke (prompt pipeline)

Validates routing + `render_prompt` for UUID webhook fixtures (no Cursor, no queue writes):

```bash
python scripts/automation_cycle_smoke.py
python scripts/automation_cycle_smoke.py --group state_changed
python scripts/automation_cycle_smoke.py --live-compressor   # requires Ollama
```

Fixtures: `automation/examples/cycle-smoke/`. Includes combined state+label case (`A-combined-in-review-impl-done`) to ensure `impl-done→verify` beats plain `status→In Review`.
```

- [ ] **Step 2: Commit**

```bash
git add docs/agent-automation.md docs/superpowers/specs/2026-06-05-automation-cycle-smoke-design.md
git commit -m "docs(automation): cycle smoke harness and design spec"
```

---

### Task 7: Final verification gate

**Files:** (none)

- [ ] **Step 1: Run cycle smoke**

```bash
python scripts/automation_cycle_smoke.py --all
```

Expected: JSON summary `"failed": 0`, `"total": 11`.

- [ ] **Step 2: Run related pytest suite**

```bash
pytest tests/test_cycle_smoke.py tests/test_linear_router.py tests/test_job_worker_prompt.py tests/test_context_compressor.py -q
```

Expected: all passed.

- [ ] **Step 3: Compile check**

```bash
python -m compileall automation/runners/cycle_smoke.py scripts/automation_cycle_smoke.py
```

Expected: exit `0`.

---

## Spec coverage checklist

| Spec requirement | Task |
|------------------|------|
| Two parent groups (state / labels) | Task 1–2 fixtures, Task 3 |
| Combined state+label regression | `A-combined-in-review-impl-done.json`, test in Task 3 |
| render_prompt + mock compressor | Task 3 `_validate_render` |
| `--live-compressor` | Task 4 CLI |
| No queue/cursor side effects | Task 3 design (no enqueue imports) |
| Terminal ignore cases | Task 2 ignore fixtures |
| Docs | Task 6 |
| Compressor coerce prerequisite | Task 0 |

## Note on `B-backlog-spec-done`

If router ignores label-only `spec_done` on Backlog (no `labels` in `updatedFrom` diff), adjust fixture to include `updatedFrom.labelIds: []` → `["bffa…"]` or add `updatedFrom` state transition. Fix in Task 2 Step 12 sanity script before commit.
