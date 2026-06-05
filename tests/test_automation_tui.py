import builtins
import importlib.util
import threading
import time
from pathlib import Path

import pytest
from automation.runners import emit as emit_mod
from automation.runners.display_mode import resolve_display_mode
from automation.runners.event_bus import Event, EventBus
from automation.runners.runtime_state import get_runtime_state, init_runtime_state


class _Args:
    def __init__(self, *, plain=False, tui=False):
        self.plain = plain
        self.tui = tui


def test_plain_always_wins():
    assert (
        resolve_display_mode(_Args(plain=True, tui=True), stdout_isatty=True, ci=False) == "plain"
    )


def test_ci_plain_unless_tui_forced():
    assert resolve_display_mode(_Args(), stdout_isatty=True, ci=True) == "plain"
    assert resolve_display_mode(_Args(tui=True), stdout_isatty=True, ci=True) == "tui"


def test_non_tty_plain_unless_tui_forced():
    assert resolve_display_mode(_Args(), stdout_isatty=False, ci=False) == "plain"
    assert resolve_display_mode(_Args(tui=True), stdout_isatty=False, ci=False) == "tui"


def test_interactive_tty_defaults_tui():
    assert resolve_display_mode(_Args(), stdout_isatty=True, ci=False) == "tui"


def test_event_bus_tail_order_and_cap():
    bus = EventBus(capacity=3)
    for i in range(5):
        bus.append(Event(ts=time.time(), source="daemon", kind="test", summary=str(i), detail=None))
    tail = bus.tail(10)
    assert [e.summary for e in tail] == ["2", "3", "4"]


def test_event_bus_thread_safe():
    bus = EventBus(capacity=200)

    def worker(n: int):
        for i in range(50):
            bus.append(
                Event(ts=time.time(), source="worker", kind="t", summary=f"{n}-{i}", detail=None)
            )

    threads = [threading.Thread(target=worker, args=(t,)) for t in range(4)]
    for th in threads:
        th.start()
    for th in threads:
        th.join()
    assert len(bus.tail(500)) == 200


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


def test_runtime_state_snapshot_isolated_copy():
    init_runtime_state(
        webhook_enabled=True, host="127.0.0.1", port=8765, path="/linear/webhook", poll=15.0
    )
    state = get_runtime_state()
    snap1 = state.snapshot()
    state.active_job_id = "job-1"
    snap2 = state.snapshot()
    assert snap1.active_job_id is None
    assert snap2.active_job_id == "job-1"


def test_ensure_rich_available_raises_on_import_error(monkeypatch):
    from automation.runners.tui_dashboard import ensure_rich_available

    real_import = builtins.__import__

    def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "rich":
            raise ImportError("no rich")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", guarded_import)
    with pytest.raises(RuntimeError, match="Rich is required for --tui"):
        ensure_rich_available()


def test_build_layout_renders_without_error():
    from automation.runners.runtime_state import RuntimeState
    from automation.runners.tui_dashboard import build_layout

    state = RuntimeState.initial(
        webhook_enabled=False, host="127.0.0.1", port=8765, path="/x", poll=15.0
    )
    snap = state.snapshot()
    layout = build_layout(snap, [], [], terminal_width=140)
    assert layout is not None
    layout_narrow = build_layout(snap, [], [], terminal_width=80)
    assert layout_narrow is not None


def test_read_log_tail_returns_last_lines(tmp_path):
    from automation.runners.log_tail import read_log_tail

    log = tmp_path / "job.log"
    log.write_text("line1\nline2\nline3\n", encoding="utf-8")
    lines, age = read_log_tail(str(log), max_lines=2)
    assert lines == ["line2", "line3"]
    assert age is not None
    assert age >= 0.0


def test_format_event_display_compresses_webhook():
    from automation.runners.tui_dashboard import format_event_display

    event = Event(
        ts=time.time(),
        source="webhook",
        kind="webhook.post",
        summary=(
            "POST /linear/webhook issue=NOV-20 status=queued "
            "job_id=linear-NOV-20-in-progress-implement-02 msg=Enqueued"
        ),
        detail=None,
    )
    row = format_event_display(event)
    assert "NOV-20" in row
    assert "queued" in row
    assert "linear-NOV-20-in-progress" not in row


def test_agent_panel_tails_log_when_buffered():
    from automation.runners.runtime_state import RuntimeState
    from automation.runners.tui_dashboard import _build_agent_panel

    state = RuntimeState.initial(
        webhook_enabled=True, host="127.0.0.1", port=8765, path="/x", poll=15.0
    )
    state.cursor_running = True
    state.cursor_output_buffered = True
    state.log_path = __file__
    state.job_started_at = time.time() - 90
    state.cursor_pid = 4242
    state.git_changed_count = 2
    state.git_status_lines = (" M automation/runners/tui_dashboard.py",)
    snap = state.snapshot()
    text = _build_agent_panel(snap, [], log_tail=["stdout: working", "stderr: ok"], log_age_s=2.0)
    assert "cursor-agent running" in text
    assert "log updated 2s ago" in text
    assert "pid 4242" in text
    assert "Changed files (2):" in text
    assert "stdout: working" in text


def test_filter_log_content_skips_metadata():
    from automation.runners.tui_dashboard import _filter_log_content

    lines = ["prompt_log: x", "delivery: subprocess", "real output line"]
    assert _filter_log_content(lines) == ["real output line"]


def test_read_git_status_short_empty_repo(tmp_path):
    from automation.runners.git_snapshot import read_git_status_short

    count, lines = read_git_status_short(str(tmp_path))
    assert count == 0
    assert lines == []


def test_parse_pid_lock_file_accepts_json_and_pid_line(tmp_path):
    from automation.runners.worker_lock import parse_pid_lock_file

    json_lock = tmp_path / "worker.lock"
    json_lock.write_text('{"pid": 1234, "row_id": 1}', encoding="utf-8")
    assert parse_pid_lock_file(json_lock) == 1234

    text_lock = tmp_path / "repo.lock"
    text_lock.write_text("pid=5678 ts=1\n", encoding="utf-8")
    assert parse_pid_lock_file(text_lock) == 5678


def test_clear_stale_file_lock_removes_dead_json_lock(monkeypatch, tmp_path):
    from automation.runners import worker_lock

    lock_file = tmp_path / "automation-worker.lock"
    lock_file.write_text('{"pid": 1234, "row_id": 1}', encoding="utf-8")
    monkeypatch.setattr(worker_lock, "_pid_alive", lambda pid: False)

    assert worker_lock.clear_stale_file_lock(lock_file) is True
    assert not lock_file.exists()


def test_header_includes_compact_queue_line():
    from automation.runners.runtime_state import RuntimeState
    from automation.runners.tui_dashboard import _build_header

    snap = RuntimeState.initial(
        webhook_enabled=False, host="127.0.0.1", port=8765, path="/x", poll=15.0
    ).snapshot()
    header = _build_header(snap)
    assert "Queue: queued" in header
    assert "·" in header


def _load_automation_daemon():
    root = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location(
        "automation_daemon",
        root / "scripts" / "automation_daemon.py",
    )
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_streaming_tee_invokes_on_line(monkeypatch, tmp_path):
    from automation.runners import cursor_runner

    lines: list[tuple[str, str]] = []

    class FakeProc:
        returncode = None

        def __init__(self):
            self._polls = 0
            self.stdout = None
            self.stderr = None
            self.stdin = None

        def poll(self):
            self._polls += 1
            if self._polls < 5:
                return None
            return 0

        def wait(self, timeout=None):
            return 0

        def terminate(self):
            pass

        def kill(self):
            pass

    def fake_popen(*_args, **_kwargs):
        return FakeProc()

    def fake_read_stream(_stream, stream_name, on_line, line_list, _log_file):
        on_line(stream_name, "hello")
        line_list.append("hello\n")

    monkeypatch.setattr(cursor_runner.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(cursor_runner, "resolve_cli", lambda _cfg: ["/fake/cursor"])
    monkeypatch.setattr(cursor_runner, "_read_stream", fake_read_stream)
    monkeypatch.setattr(cursor_runner, "_write_stdin", lambda _proc, _prompt: None)

    cfg = {"logs": {"dir": str(tmp_path / "logs")}}
    result = cursor_runner.run_prompt_streaming(
        tmp_path,
        "prompt body",
        cfg,
        on_line=lambda stream, line: lines.append((stream, line)),
    )

    assert ("stdout", "hello") in lines
    assert result.returncode == 0
    assert result.stdout == "hello\n"
    assert result.interrupted is False


def test_daemon_exits_2_when_rich_unavailable(monkeypatch, capsys):
    daemon = _load_automation_daemon()

    monkeypatch.setattr("automation.runners.config.load_config", lambda path=None: {})

    def boom():
        raise RuntimeError('Rich is required for --tui. Install: pip install -e ".[automation]"')

    monkeypatch.setattr("automation.runners.tui_dashboard.ensure_rich_available", boom)

    code = daemon.main(["--tui", "--strict-signals", "--no-webhook"])
    assert code == 2
    assert "Rich is required for --tui" in capsys.readouterr().err


def test_stop_event_breaks_idle_worker_loop(monkeypatch):
    daemon = _load_automation_daemon()
    calls: list[int] = []

    def fake_run_once(cfg, quiet_idle=True):
        calls.append(1)
        return False

    monkeypatch.setattr("automation.runners.job_worker.run_once", fake_run_once)
    emit_mod.init_emit(mode="tui", bus=EventBus())

    stop_event = threading.Event()
    stop_event.set()
    daemon._worker_loop(
        cfg={},
        poll=0.05,
        webhook_enabled=False,
        host="127.0.0.1",
        port=8765,
        path="/linear/webhook",
        stop_event=stop_event,
        display_mode="tui",
        bus=EventBus(),
    )
    assert calls == []


def test_stop_event_cancel_on_interrupt(monkeypatch):
    from automation.runners import worker_context
    from automation.runners.job_worker import run_once

    stop_event = threading.Event()
    worker_context.set_stop_event(stop_event)
    stop_event.set()

    cancel_called: list[int] = []
    requeue_called: list[int] = []

    monkeypatch.setattr(
        "automation.runners.job_worker.is_cursor_proc_running",
        lambda: True,
    )
    monkeypatch.setattr(
        "automation.runners.cursor_runner.request_cancel",
        lambda: cancel_called.append(1),
    )

    class FakeRecord:
        row_id = 1
        payload = {
            "id": "test-1",
            "repo": "novelguard",
            "kind": "implement",
            "task": "do thing",
        }

    class FakeQueue:
        def __init__(self):
            self._claimed = False

        def recover_orphaned_running(self, locks_dir):
            pass

        def claim_next(self):
            if not self._claimed:
                self._claimed = True
                return FakeRecord()
            return None

        def requeue_row(self, row_id):
            requeue_called.append(row_id)

        def complete(self, *args, **kwargs):
            pass

    monkeypatch.setattr("automation.runners.job_worker._queue", lambda cfg: FakeQueue())
    monkeypatch.setattr("automation.runners.job_worker.render_prompt", lambda *a, **k: "prompt")
    monkeypatch.setattr("automation.runners.job_worker.write_lock", lambda *a, **k: None)
    monkeypatch.setattr("automation.runners.job_worker.clear_lock", lambda *a: None)

    def fake_process_job(*args, **kwargs):
        raise KeyboardInterrupt()

    monkeypatch.setattr("automation.runners.job_worker.process_job", fake_process_job)
    emit_mod.init_emit(mode="tui", bus=EventBus())

    try:
        with pytest.raises(KeyboardInterrupt):
            run_once({})
    finally:
        worker_context.set_stop_event(None)

    assert cancel_called == [1]
    assert requeue_called == [1]


def test_webhook_crash_emits_bus_event(capsys, monkeypatch):
    bus = EventBus()
    emit_mod.init_emit(mode="tui", bus=bus)
    init_runtime_state(
        webhook_enabled=True,
        host="127.0.0.1",
        port=8765,
        path="/linear/webhook",
        poll=15.0,
    )

    crash_seen = threading.Event()

    def boom(*_args, **_kwargs):
        raise RuntimeError("webhook boom")

    monkeypatch.setattr("automation.linear.webhook_server.serve", boom)

    original_append = bus.append

    def tracking_append(ev):
        original_append(ev)
        if ev.kind == "webhook.crashed":
            crash_seen.set()

    monkeypatch.setattr(bus, "append", tracking_append)

    daemon = _load_automation_daemon()
    stop_event = threading.Event()
    daemon._start_webhook_background(
        "127.0.0.1",
        8765,
        restart_delay=30.0,
        stop_event=stop_event,
    )

    try:
        assert crash_seen.wait(timeout=2.0)
    finally:
        stop_event.set()
    out, err = capsys.readouterr()
    assert out == ""
    assert "FATAL: webhook background crashed" not in err
    assert get_runtime_state().webhook_status == "crashed"
    events = bus.tail(10)
    assert any(e.kind == "webhook.crashed" and "webhook boom" in e.summary for e in events)


def test_webhook_crash_restarts(monkeypatch):
    bus = EventBus()
    emit_mod.init_emit(mode="tui", bus=bus)
    init_runtime_state(
        webhook_enabled=True,
        host="127.0.0.1",
        port=8765,
        path="/linear/webhook",
        poll=15.0,
    )

    calls = 0
    restarted = threading.Event()
    stop_event = threading.Event()

    def serve_once_then_stop(*_args, **_kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("webhook boom")
        stop_event.set()
        restarted.set()

    monkeypatch.setattr("automation.linear.webhook_server.serve", serve_once_then_stop)

    daemon = _load_automation_daemon()
    daemon._start_webhook_background(
        "127.0.0.1",
        8765,
        restart_delay=0.01,
        stop_event=stop_event,
    )

    assert restarted.wait(timeout=2.0)
    assert calls == 2
    events = bus.tail(10)
    assert any(e.kind == "webhook.crashed" for e in events)
    assert any(e.kind == "webhook.restarting" for e in events)
