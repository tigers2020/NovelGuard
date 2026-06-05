---
title: Automation daemon Rich TUI dashboard
status: approved
date: 2026-06-05
related_docs:
  - automation/README.md
  - docs/agent-automation.md
---

# Automation daemon Rich TUI dashboard

## Goal

Replace sparse `[daemon]` / `[worker]` line logs in interactive PowerShell with a **read-only Rich Live dashboard** inside the same terminal started by `run-automation.ps1`. Show queue health, Linear webhook trail, worker lifecycle, live cursor-agent output (when unbuffered), verify progress, and final job status — while preserving the existing daemon lifecycle, Windows/Python 3.14 workarounds, and a `--plain` fallback identical to today’s behavior.

## Non-goals

| Item | Reason |
|------|--------|
| Browser or NovelGuard `web/` UI | User chose same-terminal TUI |
| Queue admin actions (release, reset) | Read-only v1 |
| Persisting EventBus to SQLite | Live-only; job logs remain durable history |
| Replacing `automation_queue_admin.py` | Complementary JSON CLI |
| Changing webhook HTTP contract | Out of scope |

---

## User choices (brainstorm lock)

| Decision | Choice |
|----------|--------|
| Monitor | Queue + live cursor stream + Linear webhook trail |
| Surface | Same PowerShell terminal as daemon |
| Controls | Read-only (Ctrl+C stops daemon) |
| Approach | Rich `Live` dashboard (not Textual, not ANSI watch) |

---

## CLI flags and mode selection

Add to `scripts/automation_daemon.py`:

| Flag | Behavior |
|------|----------|
| `--plain` | **Hard override.** Line-oriented `print` logs only; no Rich Live. |
| `--tui` | Force Rich Live even when auto-detection would choose plain. |

**Mode resolution order (after argparse):**

```text
1. --plain           => plain
2. CI=true           => plain, unless --tui is explicitly passed
3. non-TTY stdout    => plain, unless --tui is explicitly passed
4. --tui             => tui
5. interactive TTY   => tui
6. otherwise         => plain
```

If `--tui` is explicitly requested but Rich cannot initialize (import error, console incompatible), fail early with a clear **stderr** message and **exit code 2**.

`resolve_display_mode(args, *, stdout_isatty: bool, ci: bool) -> Literal["plain", "tui"]` lives in `automation/runners/display_mode.py` (unit-tested).

`--debug-interrupts` diagnostics use `emit_or_print()` like all other daemon output so they appear in the event trail under TUI without corrupting the Live renderer.

### Additional constraints (architecture review lock)

- **TUI mode changes terminal ownership only, not automation semantics.** Rich Live owns terminal output after initialization. Background threads must emit events/state only.
- **Print boundary:**
  - **Pre-Live:** stderr/stdout `print` allowed for fatal initialization errors (lock conflict, config missing, Rich init failure).
  - **During Live:** no direct background `print`; all diagnostics via `emit_or_print` → EventBus.
  - **Post-Live:** final shutdown line(s) may `print` normally (e.g. `[daemon] stopped (interrupt)`).

---

## Preserved daemon lifecycle (must not regress)

Order and semantics unchanged:

1. `load_config()`
2. `acquire_daemon_lock(locks_dir)` → exit `1` on conflict
3. `release_stale_locks(cfg)`
4. Optional webhook via `_start_webhook_background()` using **`_thread.start_new_thread`** (not `threading.Thread.start()` — Python 3.14/Windows hang workaround)
5. Main loop: `run_once(cfg, quiet_idle=True)` + `time.sleep(poll)` with existing idle tick / stats heartbeat logic (plain mode only for heartbeat prints)
6. `KeyboardInterrupt` → exit `130`, `release_daemon_lock` in `finally`

**Unchanged:**

- Windows startup SIGINT shield (`_WIN_DEFAULT_SIGINT_IGNORE`, `--strict-signals`, `--ignore-startup-sigint`)
- `_install_signal_handlers` + debug interrupt tracing
- Python 3.14/Windows warning print
- `--no-webhook` disables webhook thread; worker poll loop still runs
- `NOVELGUARD_AUTOMATION_DAEMON=1` env

**TUI integration:** Rich `Live` runs on the **main thread** after startup diagnostics complete. The existing `while True: run_once(...)` loop moves to a **background worker thread** when `mode == tui`.

### Worker thread shutdown contract (TUI mode)

TUI mode introduces a shared **`stop_event: threading.Event`** (StopToken).

**On Ctrl+C (main thread):**

1. Exit Rich `Live` cleanly (context manager `__exit__`).
2. Set `stop_event`.
3. If **no cursor subprocess** is active: worker loop exits after the current `run_once` boundary (between poll iterations).
4. If **cursor subprocess is active**: `cursor_runner` receives a cancellation request via the same `stop_event` (or dedicated cancel event wired to worker); worker preserves existing **`KeyboardInterrupt` → `queue.requeue_row`** semantics where applicable, or marks job failed with `interrupted` if requeue is unsafe.
5. Join worker thread (bounded timeout, e.g. 30s while cursor active, 5s idle).
6. `release_daemon_lock` in `finally` (unchanged).
7. Process exits **130**.

**Plain mode:** unchanged — main thread runs `run_once` directly; `KeyboardInterrupt` in `run_once` still requeues as today.

---

## New modules

### `automation/runners/event_bus.py`

Thread-safe, in-process, **live-only** ring buffer.

```python
@dataclass(frozen=True)
class Event:
    ts: float
    source: Literal["daemon", "webhook", "worker", "cursor", "verify"]
    kind: str          # e.g. "webhook.queued", "worker.claimed", "cursor.line"
    summary: str       # one-line for Events panel
    detail: str | None # optional multi-line (not shown in panel by default)
```

- Capacity: ~500 events; drop oldest on overflow.
- `append(event)` and `tail(n=30, *, source=None)` for dashboard.
- `clear_cursor_tail()` when a new job starts (optional; cursor lines also age out naturally).

### `automation/runners/runtime_state.py`

Thread-safe **snapshot** for dashboard header / queue panel (not durable).

```python
@dataclass
class RuntimeState:
    webhook_enabled: bool
    webhook_status: Literal["disabled", "starting", "running", "crashed"]
    webhook_host: str
    webhook_port: int
    webhook_path: str
    poll_seconds: float
    started_at: float
    # queue (best-effort)
    queued: int | None
    running: int | None
    succeeded: int | None
    failed: int | None
    # active job (None when idle)
    active_job_id: str | None
    active_issue: str | None      # issue_identifier from payload
    active_stage: str | None      # see stages below
    active_branch: str | None
    log_path: str | None
    cursor_running: bool
    verify_running: bool
    job_started_at: float | None
    last_job_status: str | None     # succeeded | failed
    last_job_finished_at: float | None
```

**`active_stage` values:** `idle` | `claimed` | `git_prepare` | `cursor` | `verify` | `complete`

`RuntimeState` is updated by worker/webhook code; dashboard reads a copied snapshot each refresh.

### `automation/runners/emit.py`

```python
def emit_or_print(
    source: str,
    kind: str,
    summary: str,
    *,
    detail: str | None = None,
    plain_prefix: str | None = None,
) -> None:
```

- **Plain mode:** `print(plain_prefix or f"[{source}] {summary}", flush=True)` (preserve existing line formats where possible).
- **TUI mode:** `EventBus.append(...)` only — **no `print`**.
- Module holds a process-global mode flag set once at daemon startup.

### `automation/runners/tui_dashboard.py`

- Builds Rich `Layout`: header, queue, events, agent tail.
- `render(state: RuntimeState, events: list[Event], cursor_tail: list[str]) -> RenderableType`
- `run_live(loop_thread: threading.Thread, stop_event: threading.Event, ...)` — owns stdout exclusively via `rich.live.Live`.
- Refresh rate: ~4 Hz (`refresh_per_second=4`).

**Layout sketch:**

```text
┌─ NovelGuard Automation ────────────────────────────────┐
│ webhook ✓ :8765  poll 15s  uptime 12m                │
├─ Queue ─────────────────┬─ Events ───────────────────┤
│ queued: 1  running: 1   │ [webhook] NOV-42 → queued    │
│ job: NOV-42  cursor 3m  │ [worker] claimed NOV-42      │
│ branch: ai/job-NOV-42   │ [verify] ruff check …        │
├─ Agent ─────────────────┴──────────────────────────────┤
│ (last ~40 lines stdout/stderr; or "buffered — see log")│
└────────────────────────────────────────────────────────┘
```

---

## Modified modules

### `scripts/automation_daemon.py`

- Add `--plain`, `--tui`; compute mode; init `EventBus`, `RuntimeState`, `emit_or_print` mode.
- Replace startup `print` calls with `emit_or_print` (plain prefixes match current `[daemon]` text).
- **TUI path:** after lock + optional webhook start, enter `run_live()` with worker thread running the existing poll loop body.
- **Plain path:** unchanged structure (inline `while True` loop).

### `automation/linear/webhook_server.py`

- Replace `print` in `log_message` and POST handler with `emit_or_print(source="webhook", ...)`.
- On successful `process_linear_webhook`, emit kind `webhook.{result.status}` with issue id, job_id, message.
- Update `RuntimeState` queue counts best-effort from `result.queue_depth` / `active_jobs`.

### `automation/runners/job_worker.py`

- Replace `print` / `json.dumps` result dump with `emit_or_print`.
- **Plain mode only:** keep final `json.dumps(result, indent=2)` for parity with today.
- **TUI mode:** emit `worker.complete` with compact summary (status, verify_ok, log_path); no full JSON to terminal.
- Update `RuntimeState` through job lifecycle: `claimed` → `git_prepare` → `cursor` → `verify` → `complete` / idle.
- `run_once` final JSON: plain only.

### `automation/runners/cursor_runner.py`

Add `run_prompt_streaming(repo, prompt, cfg, *, on_line: Callable[[str, str], None], cancel_event: threading.Event | None = None) -> CursorRunResult`:

- `subprocess.Popen` with `stdout=PIPE`, `stderr=PIPE`, text mode.
- **`cursor_runner` owns the active `Popen` handle** (module-level or context-scoped registry). `RuntimeState` may expose `cursor_pid` / `cursor_running` for display only.
- **Dashboard is read-only:** TUI renderer must **not** kill processes or mutate jobs directly. Cancellation is requested through `cancel_event` / `stop_event` wired from daemon → worker → `cursor_runner`.
- Reader threads invoke `on_line(stream, line)` per line.
- When `cancel_event` is set: terminate process (platform-appropriate: `terminate()` then `kill()` after grace), drain pipes, return non-zero `returncode` with `interrupted=True` in result metadata.
- **Tee:** append each line to an open job log file **and** `EventBus` (`source=cursor`, `kind=cursor.line`).
- On completion, write full log footer (command, returncode) as today.
- **Buffered output fallback:** if no cursor lines arrive for N seconds while process alive, dashboard shows `cursor_running=True`, elapsed time, `log_path`, and panel text: `Agent output buffered — tail: <log_path>`.
- Keep existing `run_prompt()` for plain mode / tests; `job_worker` uses streaming when TUI mode active.

### `scripts/automation_daemon.py` — webhook background crash

`_start_webhook_background()` inner `_run()` today prints traceback to stderr and re-raises on crash.

**TUI mode:** catch `BaseException`, emit `EventBus` fatal event (`daemon.webhook_crashed`), set `RuntimeState.webhook_status="crashed"`, do **not** `print` traceback (detail may go in `Event.detail`).

**Plain mode:** keep current stderr traceback + raise behavior.

`_thread.start_new_thread` startup mechanism is **unchanged**.

### `automation/runners/job_worker.py` — `run_verify`

- Before/after each verify command: `emit_or_print(source="verify", ...)`, set `RuntimeState.verify_running`.
- On failure, emit `verify.fail` with command + returncode summary.

---

## Queue stats — best-effort

- Dashboard refresh calls `_queue(cfg).stats()` inside try/except.
- On any error: render `?` for counts; do not crash Live loop.
- Same policy as today’s idle heartbeat (`stats.get('queued', '?')`).

---

## Output ownership rules (TUI mode)

| Phase | Rule |
|-------|------|
| Pre-Live | Fatal init may `print` to stderr (lock conflict, Rich init failure) |
| During Live | Rich Live owns stdout; background threads use `emit_or_print` only |
| Post-Live | Shutdown/fatal lines may `print` normally |

| Rule | Enforcement |
|------|-------------|
| No background `print` during Live | All hot-path modules use `emit_or_print` |
| Webhook thread | `log_message` → `emit_or_print`; crash → EventBus + `webhook_status=crashed` |
| Cursor cancel | Only `cursor_runner` terminates its `Popen`; not the dashboard |

`BaseHTTPRequestHandler.log_message` override must call `emit_or_print`, not `print`.

---

## Data flow

```text
Linear POST → webhook_server → process_linear_webhook → EventBus + RuntimeState
                                    ↓
                              queue.enqueue
                                    ↓
worker thread → run_once → claim → RuntimeState(stage=claimed)
                    ↓
              process_job → git_prepare → cursor_stream → tee → log file + EventBus
                    ↓
              run_verify → EventBus per command
                    ↓
              queue.complete → EventBus(worker.complete) + RuntimeState idle
                    ↓
main thread Live refresh ← read RuntimeState + EventBus.tail + cursor_tail
```

**Durable history:** `automation/logs/job-<id>-<ts>.log` (unchanged). EventBus is not replayed after restart.

---

## Error handling

| Case | Behavior |
|------|----------|
| Worker exception in TUI loop | `emit_or_print` error; `RuntimeState` reset active job; continue poll loop |
| Webhook handler 500 | Event `webhook.error`; HTTP response unchanged |
| Cursor CLI missing | `worker` fail event; job completes `failed` as today |
| Ctrl+C during job (plain) | `KeyboardInterrupt` in `run_once` → `requeue_row`; exit 130 |
| Ctrl+C during job (TUI) | `stop_event` → cancel cursor if active; worker honors requeue at `run_once` boundary; Live exits; exit 130 |
| Ctrl+C idle (TUI) | `stop_event` → worker exits after current `run_once`/sleep boundary |
| Webhook thread crash (TUI) | `webhook_status=crashed`; fatal event in bus; no stderr traceback |
| `--tui` + Rich init fail | stderr message; exit **2** |
| Queue sqlite locked | Stats show `?`; worker error event if claim fails |
| Daemon lock conflict | Pre-TUI exit `1` with message (plain print to stderr — before Live starts) |

Lock conflict and early startup failures occur **before** Rich Live starts; use plain `print` to stderr so the user sees the error.

---

## Dependencies

```toml
# pyproject.toml [project.optional-dependencies]
automation = [
    "pyyaml>=6.0",
    "rich>=13.0",
]
```

Document in `automation/README.md`: `pip install -e ".[automation]"` for TUI.

---

## Acceptance criteria

1. Interactive PowerShell (`run-automation.ps1`, TTY, no `--plain`) defaults to Rich dashboard.
2. `--plain` preserves current line-oriented logs (including idle heartbeat and final JSON result).
3. `--no-webhook` still works; dashboard header shows webhook **disabled**.
4. Ctrl+C exits cleanly with code **130** and releases daemon lock.
5. Live visibility: Linear webhook trail, queue stats, worker claimed state, cursor stream (or buffered fallback), verify steps, final status.
6. No background `print` corruption in TUI mode (no interleaved raw lines).
7. Python 3.14/Windows warning and SIGINT startup shield remain intact.
8. `_thread.start_new_thread` webhook startup preserved (no `Thread.start()`).
9. Non-TTY / `CI` env falls back to plain unless `--tui` explicitly passed.
10. `--tui` in non-TTY with Rich init failure exits **2** with clear stderr message.
11. Ctrl+C during active cursor job preserves requeue/failure semantics via `cursor_runner` cancellation (not dashboard kill).
12. Webhook background crash surfaces in EventBus + `RuntimeState.webhook_status` without corrupting Live layout.

**Plan:** [2026-06-05-automation-tui-dashboard.md](../plans/2026-06-05-automation-tui-dashboard.md)

---

## Testing

| Test | Type | Assert |
|------|------|--------|
| `resolve_display_mode(plain=True)` | unit | plain |
| `resolve_display_mode(tty, no flags)` | unit | tui |
| `resolve_display_mode(not tty, no --tui)` | unit | plain |
| `resolve_display_mode(not tty, --tui)` | unit | tui |
| `resolve_display_mode(CI=true, --tui)` | unit | tui |
| `resolve_display_mode(CI=true, no --tui)` | unit | plain |
| cursor cancel on `stop_event` | unit | terminate + interrupted result |
| webhook crash handler (TUI) | unit | bus event + webhook_status, no print |
| `EventBus` thread safety | unit | concurrent append, ordered tail |
| `emit_or_print` plain | unit | calls print, no bus |
| `emit_or_print` tui | unit | appends bus, no print |
| `RuntimeState` snapshot copy | unit | isolated read |
| `cursor_runner` streaming tee | unit | mock Popen; lines → callback + file |
| Daemon lock + `--plain --once` smoke | manual | existing behavior |
| Interactive TUI smoke | manual | dashboard renders; webhook + job cycle |

Target: `pytest tests/test_automation_tui.py -v` (new file, no web).

---

## Rollout

1. Land modules (`event_bus`, `runtime_state`, `emit`, `tui_dashboard`) + unit tests.
2. Wire `emit_or_print` through webhook + worker + cursor (streaming).
3. Integrate daemon main-thread Live + worker thread.
4. Update `automation/README.md` with TUI screenshot/description and `--plain` note.
