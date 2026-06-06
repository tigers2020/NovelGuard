# Automation Cycle Smoke (Prompt Pipeline) — Design

**Date:** 2026-06-05  
**Status:** Approved (brainstorming)  
**Depth:** B — routing + `render_prompt` + compressor (mock or live). No Cursor, queue, git, or Linear MCP.

---

## Problem

Automation cycle spans webhook routing, job payload build, and prompt rendering with optional Ollama compression. Tools exist per stage (`pytest`, `linear_webhook_handler.py test`, `automation_compressor_doctor.py`) but nothing validates a **multi-branch routing tree** end-to-end through `render_prompt()`.

## Goal

One command exercises ~12 synthetic webhook fixtures grouped by **parent event type**, asserting route → payload → rendered prompt for each case — including combined state+label webhooks where execution labels beat status-column routes.

## Non-goals

- Cursor CLI, worker `--once`, daemon, ngrok, `queue.sqlite` writes
- Linear parent/child issue hierarchy (not modeled in router today)
- Level C/D smoke (dry_run worker, full live cycle)

## Architecture

```text
manifest.json (groups + cases)
    ↓ per fixture JSON
route_linear_webhook(cfg)
    ↓
build_job_payload (if routed)
    ↓
render_prompt(cfg, payload)  [compressor: mock | live]
    ↓
assertions → report
```

**Modules:**

| File | Role |
|------|------|
| `automation/runners/cycle_smoke.py` | Core runner, validation, report dataclasses |
| `scripts/automation_cycle_smoke.py` | CLI (`--live-compressor`, `--group`, `--all`) |
| `automation/examples/cycle-smoke/manifest.json` | Case index |
| `automation/examples/cycle-smoke/*.json` | UUID-style webhook payloads |

## Routing parents (control plane)

Two parent event types in `automation/linear/router.py`:

1. **`state_changed`** (`updatedFrom.stateId`) — execution labels first, then planning, then status column (`In Progress` → implement, `In Review` → verify).
2. **`labels_changed` only** — execution, planning, or `_route_label_only_execution` (label diff).

When **both** change in one webhook, only the `state_changed` branch runs; label-diff routing is skipped.

### Combined regression case (required)

Fixture `A-combined-in-review-impl-done.json`:

- `updatedFrom`: `stateId` (In Progress) **and** `labelIds` without `impl_done`
- `data`: `stateId` In Review + `labelIds` includes new `impl_done`
- **Expect:** `linear/in-review/verify.md`, reason contains `impl-done→verify` (not plain `status→In Review`)

Contrast `A4-pure-in-review.json` (state only, no `impl_done`) → reason `status→In Review`.

## Manifest groups (~12 cases)

| Group | Cases |
|-------|--------|
| `state_changed` | in-progress, pure in-review, combined state+impl_done, in-progress+impl_done exec |
| `labels_only` | impl-done diff, todo-list-done, plan-done, research-done, backlog spec-done |
| `terminal` | verify-done → ignore, Done status → ignore |

Synthetic issue identifier: **`NOV-SMOKE`** for all fixtures.

## Per-case validation

1. **Route:** `expect_prompt` matches `route.prompt_file`, or `expect_route: null` when ignored.
2. **Reason:** optional `expect_reason_contains` substring.
3. **Payload:** `task` non-empty; `meta.route_reason` present when routed.
4. **Render:** no unresolved worker placeholders (`{{TASK}}`, `{{JOB_ID}}`, `{{CONTEXT_MEMORY_JSON}}`, etc.).
5. **Brief:** rendered text must reference `runner-brief-compact`, not `runner-brief.md`.
6. **Memory block:** `CONTEXT_MEMORY_JSON` section parses as JSON object (mock or live).
7. **Size:** `len(rendered) <= 24000` unless case overrides `max_chars`.

## Compressor modes

| Mode | Behavior |
|------|----------|
| Default | Mock `compress_job_context` with deterministic memory dict |
| `--live-compressor` | Real Ollama; cache under `automation/context_cache/_smoke/<case-id>/` |

**Prerequisite:** `context_compressor` coerce fix committed before relying on `--live-compressor`.

## CLI

```bash
python scripts/automation_cycle_smoke.py
python scripts/automation_cycle_smoke.py --live-compressor
python scripts/automation_cycle_smoke.py --group state_changed
python scripts/automation_cycle_smoke.py --all   # continue on failure, summary at end
```

Exit `0` when all cases pass; `1` on any failure (unless `--all` with failures).

## Testing

- `tests/test_cycle_smoke.py` imports `automation.runners.cycle_smoke` and runs manifest with mock compressor (CI-safe).
- Commit new tests with `ALLOW_NEW_TESTS=1`.

## Documentation

Add **Cycle smoke** subsection to `docs/agent-automation.md` with command and group description.
