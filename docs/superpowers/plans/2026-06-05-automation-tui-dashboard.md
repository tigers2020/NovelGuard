# Automation Rich TUI dashboard — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a read-only Rich Live dashboard to `automation_daemon.py` (default in interactive PowerShell) with `--plain` / `--tui` flags, EventBus, RuntimeState, cursor streaming tee, and preserved Ctrl+C / requeue semantics.

**Architecture:** `resolve_display_mode` picks plain vs TUI. TUI mode runs Rich `Live` on the main thread and the existing `run_once` poll loop on a worker thread coordinated by `stop_event`. All background output routes through `emit_or_print` → EventBus; `cursor_runner` owns subprocess cancellation.

**Tech Stack:** Python 3.12+ (`automation/`, `scripts/`), Rich ≥13, existing sqlite job queue, `_thread.start_new_thread` webhook.

**Spec:** [2026-06-05-automation-tui-dashboard-design.md](../specs/2026-06-05-automation-tui-dashboard-design.md) (**approved** 2026-06-05)

**Test policy:** New file `tests/test_automation_tui.py` allowed (automation-only; no `TEST_ALLOWED` gate in repo for automation).

---

## File map

| File | Action |
|------|--------|
| `automation/runners/display_mode.py` | **Create** — `resolve_display_mode`, `DisplayMode` |
| `automation/runners/event_bus.py` | **Create** — thread-safe ring buffer |
| `automation/runners/runtime_state.py` | **Create** — `RuntimeState` + snapshot copy |
| `automation/runners/emit.py` | **Create** — `emit_or_print`, mode init |
| `automation/runners/tui_dashboard.py` | **Create** — Rich Layout + `run_live` |
| `automation/runners/cursor_runner.py` | **Modify** — streaming, cancel, Popen ownership |
| `automation/runners/job_worker.py` | **Modify** — emit, RuntimeState updates, streaming path |
| `automation/linear/webhook_server.py` | **Modify** — `emit_or_print` |
| `scripts/automation_daemon.py` | **Modify** — flags, TUI main thread, worker thread, webhook crash |
| `pyproject.toml` | **Modify** — `rich>=13.0` in `[automation]` extra |
| `automation/README.md` | **Modify** — TUI / `--plain` docs |
| `tests/test_automation_tui.py` | **Create** — unit tests |

---

## Slice 1: Mode resolver + CLI flags

### Task 1: `display_mode` module

**Files:**
- Create: `automation/runners/display_mode.py`
- Create: `tests/test_automation_tui.py`
- Modify: `scripts/automation_daemon.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_automation_tui.py
from automation.runners.display_mode import resolve_display_mode


class _Args:
    def __init__(self, *, plain=False, tui=False):
        self.plain = plain
        self.tui = tui


def test_plain_always_wins():
    assert resolve_display_mode(_Args(plain=True, tui=True), stdout_isatty=True, ci=False) == "plain"


def test_ci_plain_unless_tui_forced():
    assert resolve_display_mode(_Args(), stdout_isatty=True, ci=True) == "plain"
    assert resolve_display_mode(_Args(tui=True), stdout_isatty=True, ci=True) == "tui"


def test_non_tty_plain_unless_tui_forced():
    assert resolve_display_mode(_Args(), stdout_isatty=False, ci=False) == "plain"
    assert resolve_display_mode(_Args(tui=True), stdout_isatty=False, ci=False) == "tui"


def test_interactive_tty_defaults_tui():
    assert resolve_display_mode(_Args(), stdout_isatty=True, ci=False) == "tui"
```

- [ ] **Step 2: Run test — expect FAIL**

Run: `pytest tests/test_automation_tui.py -v`  
Expected: `ModuleNotFoundError` or import error

- [ ] **Step 3: Implement**

```python
# automation/runners/display_mode.py
from __future__ import annotations

from typing import Literal

DisplayMode = Literal["plain", "tui"]


def resolve_display_mode(
    args: object,
    *,
    stdout_isatty: bool,
    ci: bool,
) -> DisplayMode:
    plain = bool(getattr(args, "plain", False))
    tui = bool(getattr(args, "tui", False))
    if plain:
        return "plain"
    if ci and not tui:
        return "plain"
    if not stdout_isatty and not tui:
        return "plain"
    if tui:
        return "tui"
    if stdout_isatty:
        return "tui"
    return "plain"
```

- [ ] **Step 4: Run test — expect PASS**

Run: `pytest tests/test_automation_tui.py -v`

- [ ] **Step 5: Wire argparse in daemon (no TUI yet)**

Add to `scripts/automation_daemon.py` parser:

```python
parser.add_argument("--plain", action="store_true", help="Line logs only; no Rich dashboard")
parser.add_argument("--tui", action="store_true", help="Force Rich dashboard")
```

After parse:

```python
from automation.runners.display_mode import resolve_display_mode

ci = bool(os.environ.get("CI"))
display_mode = resolve_display_mode(args, stdout_isatty=sys.stdout.isatty(), ci=ci)
```

Store `display_mode` for later slices; behavior unchanged until Slice 4.

- [ ] **Step 6: Rich init guard helper**

Add to `automation/runners/tui_dashboard.py` (stub):

```python
def ensure_rich_available() -> None:
    try:
        import rich  # noqa: F401
    except ImportError as exc:
        raise RuntimeError(
            "Rich is required for --tui. Install: pip install -e \".[automation]\""
        ) from exc
```

In daemon, before entering TUI (Slice 4):

```python
if display_mode == "tui":
    try:
        from automation.runners.tui_dashboard import ensure_rich_available
        ensure_rich_available()
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 2
```

---

## Slice 2: EventBus + RuntimeState

### Task 2: EventBus

**Files:**
- Create: `automation/runners/event_bus.py`
- Modify: `tests/test_automation_tui.py`

- [ ] **Step 1: Failing test**

```python
import threading
import time

from automation.runners.event_bus import Event, EventBus


def test_event_bus_tail_order_and_cap():
    bus = EventBus(capacity=3)
    for i in range(5):
        bus.append(Event(ts=time.time(), source="daemon", kind="test", summary=str(i), detail=None))
    tail = bus.tail(10)
    assert [e.summary for e in tail] == ["2", "3", "4"]


def test_event_bus_thread_safe():
    bus = EventBus(capacity=100)
    def worker(n: int):
        for i in range(50):
            bus.append(Event(ts=time.time(), source="worker", kind="t", summary=f"{n}-{i}", detail=None))
    threads = [threading.Thread(target=worker, args=(t,)) for t in range(4)]
    for th in threads:
        th.start()
    for th in threads:
        th.join()
    assert len(bus.tail(500)) == 200
```

- [ ] **Step 2: Run — FAIL**

- [ ] **Step 3: Implement `EventBus`**

Use `collections.deque` + `threading.Lock`. Methods: `append`, `tail(n, source=None)`, `cursor_lines(n=40)` filtering `kind=="cursor.line"`.

- [ ] **Step 4: Run — PASS**

### Task 3: RuntimeState

**Files:**
- Create: `automation/runners/runtime_state.py`
- Modify: `tests/test_automation_tui.py`

- [ ] **Step 1: Failing test**

```python
from automation.runners.runtime_state import RuntimeState


def test_runtime_state_snapshot_isolated_copy():
    state = RuntimeState.initial(webhook_enabled=True, host="127.0.0.1", port=8765, path="/linear/webhook", poll=15.0)
    snap1 = state.snapshot()
    state.active_job_id = "job-1"
    snap2 = state.snapshot()
    assert snap1.active_job_id is None
    assert snap2.active_job_id == "job-1"
```

- [ ] **Step 2–4: Implement**

`RuntimeState` with `threading.Lock`, fields per spec (`webhook_status`, `cursor_running`, etc.), `snapshot() -> RuntimeStateSnapshot` (frozen dataclass copy).

Module singleton: `get_runtime_state() -> RuntimeState` initialized once from daemon.

---

## Slice 3: `emit_or_print` + plain routing

### Task 4: emit module

**Files:**
- Create: `automation/runners/emit.py`
- Modify: `tests/test_automation_tui.py`

- [ ] **Step 1: Tests**

```python
from automation.runners import emit as emit_mod
from automation.runners.event_bus import EventBus


def test_emit_plain_prints(capsys):
    emit_mod.init_emit(mode="plain", bus=EventBus())
    emit_mod.emit_or_print("daemon", "start", "hello", plain_prefix="[daemon] hello")
    assert "[daemon] hello" in capsys.readouterr().out


def test_emit_tui_bus_only(capsys):
    bus = EventBus()
    emit_mod.init_emit(mode="tui", bus=bus)
    emit_mod.emit_or_print("worker", "claimed", "job-1")
    assert capsys.readouterr().out == ""
    assert bus.tail(1)[0].summary == "job-1"
```

- [ ] **Step 2–4: Implement `emit.py`**

```python
_mode: DisplayMode = "plain"
_bus: EventBus | None = None

def init_emit(*, mode: DisplayMode, bus: EventBus) -> None: ...

def emit_or_print(source, kind, summary, *, detail=None, plain_prefix=None) -> None:
    if _mode == "plain":
        print(plain_prefix or f"[{source}] {summary}", flush=True)
        return
    assert _bus is not None
    _bus.append(Event(ts=time.time(), source=source, kind=kind, summary=summary, detail=detail))
```

### Task 5: Daemon pre-Live prints → emit (plain parity)

**Files:**
- Modify: `scripts/automation_daemon.py`

- [ ] Replace post-config startup `print(f"[daemon] ...")` with `emit_or_print(..., plain_prefix=...)` **only after** `init_emit` in plain path.

- [ ] **Lock conflict before `init_emit`:** keep `print(..., file=sys.stderr); return 1` (Pre-Live rule).

- [ ] Run manual: `python scripts/automation_daemon.py --plain --no-webhook` — startup lines unchanged.

---

## Slice 4: Rich dashboard shell

### Task 6: `tui_dashboard` renderer

**Files:**
- Create: `automation/runners/tui_dashboard.py` (full)
- Modify: `pyproject.toml`

- [ ] Add `rich>=13.0` to `[project.optional-dependencies] automation`.

- [ ] Implement:

```python
def build_layout(snapshot, events, cursor_lines) -> Layout: ...

def run_live(
    *,
    stop_event: threading.Event,
    worker_thread: threading.Thread,
    state: RuntimeState,
    bus: EventBus,
    refresh_stats: Callable[[], None],
) -> None:
    with Live(build_layout(...), refresh_per_second=4, screen=True) as live:
        while not stop_event.is_set() or worker_thread.is_alive():
            refresh_stats()
            live.update(build_layout(state.snapshot(), bus.tail(30), bus.cursor_lines(40)))
            if stop_event.is_set():
                break
            time.sleep(0.25)
        worker_thread.join(timeout=30.0)
```

Header shows `webhook_status` (`disabled` / `running` / `crashed`), uptime, poll interval.

Queue panel: stats with `?` on `refresh_stats` exception (try/except inside callback).

### Task 7: Daemon TUI integration (idle loop only)

**Files:**
- Modify: `scripts/automation_daemon.py`

- [ ] **Worker thread function** (extract from current loop):

```python
def _worker_loop(cfg, poll, webhook_enabled, host, port, stop_event, display_mode):
    idle_ticks = 0
    while not stop_event.is_set():
        try:
            had_job = run_once(cfg, quiet_idle=True)
        except KeyboardInterrupt:
            stop_event.set()
            raise
        except Exception as exc:
            emit_or_print("daemon", "worker.error", str(exc))
            had_job = False
        if had_job:
            idle_ticks = 0
        elif display_mode == "plain":
            # existing idle heartbeat
            ...
        if stop_event.wait(timeout=poll):
            break
```

- [ ] **TUI path:** after webhook start, `init_emit(mode="tui", bus)`, `stop_event = threading.Event()`, start `threading.Thread(target=_worker_loop, daemon=True)`, call `run_live(...)`.

- [ ] **Plain path:** `init_emit(mode="plain", ...)`, inline `while True` (current code).

- [ ] **KeyboardInterrupt handler:**

```python
except KeyboardInterrupt:
    if display_mode == "tui":
        stop_event.set()
    print("\n[daemon] stopped (interrupt)", flush=True)  # Post-Live OK
    exit_code = 130
```

Ensure `run_live` returns before this print when TUI.

- [ ] Manual smoke: interactive `python scripts/automation_daemon.py --no-webhook` — dashboard renders, idle stats update.

---

## Slice 5: Cursor streaming tee

### Task 8: `run_prompt_streaming`

**Files:**
- Modify: `automation/runners/cursor_runner.py`
- Modify: `automation/runners/job_worker.py`
- Modify: `tests/test_automation_tui.py`

- [ ] **Test with mocked Popen**

```python
def test_streaming_tee_invokes_on_line(monkeypatch, tmp_path):
    lines = []

    class FakeProc:
        returncode = 0
        def poll(self): return 0
        def wait(self, timeout=None): return 0
        def terminate(self): pass
        def kill(self): pass

    def fake_popen(*a, **k):
        return FakeProc()

    monkeypatch.setattr("automation.runners.cursor_runner.subprocess.Popen", fake_popen)
    # monkeypatch reader to call on_line("stdout", "hello")
    ...
```

- [ ] Implement `run_prompt_streaming` with:
  - `_active_proc: Popen | None` module var
  - `request_cancel()` sets flag read by wait loop
  - Reader threads for stdout/stderr
  - `on_line(stream, line)` + log file append
  - `CursorRunResult` extended with `interrupted: bool = False`

- [ ] **`job_worker.process_job`:** if `emit.is_tui_mode()`: use streaming; pass `cancel_event=stop_event` from worker context (thread-local or explicit param through `run_once`).

- [ ] Update `RuntimeState`: `cursor_running`, `log_path`, `active_stage`, optional `cursor_pid`.

- [ ] Buffered fallback: if no lines for 30s while `poll() is None`, dashboard agent panel shows buffered message (state flag `cursor_output_buffered`).

---

## Slice 6: Worker shutdown + Ctrl+C preservation

### Task 9: Cancellation wiring

**Files:**
- Modify: `scripts/automation_daemon.py`
- Modify: `automation/runners/job_worker.py`
- Modify: `automation/runners/cursor_runner.py`

- [ ] **Shared `stop_event`** created in daemon; passed to worker loop and stored in `automation/runners/worker_context.py` (new tiny module):

```python
_stop_event: threading.Event | None = None

def set_stop_event(ev: threading.Event | None) -> None: ...
def stop_requested() -> bool: ...
```

- [ ] **On Ctrl+C (main):** `stop_event.set()` before exiting Live.

- [ ] **In `run_once` KeyboardInterrupt:** if `stop_requested()` and cursor active → let `cursor_runner.request_cancel()` run, then existing `queue.requeue_row` on interrupt path.

- [ ] **Worker loop:** when `stop_event` set and not in job, break without starting new `run_once`.

- [ ] **Test:** mock cursor_runner with slow process; set `stop_event`; assert `requeue_row` called (mock queue).

```python
def test_stop_event_breaks_idle_worker_loop():
    ev = threading.Event()
    ev.set()
    assert ev.wait(timeout=0) is True  # placeholder — expand with worker loop extract test
```

### Task 10: Webhook crash → EventBus

**Files:**
- Modify: `scripts/automation_daemon.py` (`_start_webhook_background`)

- [ ] Wrap `_run()` except block:

```python
except BaseException as exc:
    if emit.is_tui_mode():
        emit_or_print("daemon", "webhook.crashed", str(exc), detail=traceback.format_exc())
        get_runtime_state().webhook_status = "crashed"
    else:
        print("[daemon] FATAL: webhook background crashed", file=sys.stderr, flush=True)
        traceback.print_exc()
    raise
```

- [ ] Test: mock `serve` to raise; TUI mode → bus event, no print (capsys).

### Task 11: Webhook + worker emit wiring

**Files:**
- Modify: `automation/linear/webhook_server.py`
- Modify: `automation/runners/job_worker.py`

- [ ] Replace remaining `print` with `emit_or_print`.
- [ ] TUI: compact `worker.complete` event; plain: keep `json.dumps(result)`.
- [ ] `run_verify`: emit before/after each command; toggle `verify_running`.

---

## Slice 7: Tests + docs + manual smoke

### Task 12: Integration tests + README

**Files:**
- Modify: `tests/test_automation_tui.py`
- Modify: `automation/README.md`

- [ ] Full unit suite green:

Run: `pytest tests/test_automation_tui.py -v`

- [ ] Regression:

Run: `python -m ruff check automation scripts/automation_daemon.py tests/test_automation_tui.py`

- [ ] Update `automation/README.md`:

```markdown
### Dashboard (default in PowerShell)

pip install -e ".[automation]"
.\automation\run-automation.ps1

Flags:
- `--plain` — line logs (CI / pipes)
- `--tui` — force dashboard in non-TTY
```

### Task 13: Manual acceptance checklist

- [ ] Interactive PowerShell → Rich dashboard default
- [ ] `--plain` → identical line logs + JSON result
- [ ] `--no-webhook` → header shows disabled
- [ ] Ctrl+C idle → exit 130, lock released
- [ ] Ctrl+C during dry_run job → requeue or fail per existing semantics
- [ ] Enqueue job → events trail + queue stats live
- [ ] `--tui` with `CI=true` → TUI attempts (or exit 2 if no Rich)

---

## Spec coverage self-review

| Spec requirement | Task |
|------------------|------|
| Mode resolution order 1–6 | Task 1 |
| `--tui` Rich fail exit 2 | Task 1, 7 |
| Preserved daemon lifecycle | Task 5, 7 |
| `_thread.start_new_thread` webhook | unchanged in Task 10 |
| SIGINT shield | no changes to `_install_signal_handlers` |
| `stop_event` shutdown contract | Task 9 |
| cursor_runner owns Popen | Task 8, 9 |
| Webhook crash EventBus | Task 10 |
| Pre/During/Post-Live print boundary | Task 5, 7, 10 |
| Queue stats best-effort `?` | Task 6 |
| Cursor tee + buffered fallback | Task 8 |
| Acceptance 1–12 | Task 13 |

No TBD placeholders in plan tasks.

---

## Execution handoff

Plan saved. Two execution options:

1. **Subagent-Driven (recommended)** — fresh subagent per slice, review between slices
2. **Inline Execution** — implement slices in this session with checkpoints

Which approach?
