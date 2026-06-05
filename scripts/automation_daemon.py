#!/usr/bin/env python3
"""Linear webhook receiver + job worker in one long-lived process.

Usage:
  python scripts/automation_daemon.py
  python scripts/automation_daemon.py --debug-interrupts

Requires ngrok forwarding to linear.webhook_port (default 8765):
  ngrok http 8765
"""

from __future__ import annotations

import argparse
import os
import signal
import sys
import threading
import time
import traceback
from pathlib import Path
from types import FrameType
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from automation.runners.event_bus import EventBus


def _install_signal_handlers(*, startup_ignore_seconds: float, debug: bool) -> None:
    """Ignore spurious startup SIGINT (Windows/Cursor) and optionally trace sources."""
    startup_time = time.monotonic()

    def _on_signal(signum: int, frame: FrameType | None) -> None:
        age = time.monotonic() - startup_time
        if debug:
            where = "unknown"
            if frame is not None:
                where = f"{frame.f_code.co_filename}:{frame.f_lineno}"
            print(
                f"\n[daemon] DEBUG: received signal {signum} after {age:.2f}s at {where}",
                file=sys.stderr,
                flush=True,
            )
            if frame is not None:
                traceback.print_stack(frame)
        if startup_ignore_seconds > 0 and age < startup_ignore_seconds:
            print(
                f"[daemon] WARN: ignoring spurious SIGINT ({age:.2f}s < {startup_ignore_seconds:.1f}s)",
                file=sys.stderr,
                flush=True,
            )
            return
        raise KeyboardInterrupt

    signal.signal(signal.SIGINT, _on_signal)
    if hasattr(signal, "SIGBREAK"):
        signal.signal(signal.SIGBREAK, _on_signal)

    if not debug:
        return

    try:
        import _thread as _thread_mod

        _original_interrupt_main = _thread_mod.interrupt_main

        def _debug_interrupt_main(*args: object, **kwargs: object) -> None:
            print(
                "\n[daemon] DEBUG: _thread.interrupt_main() called",
                file=sys.stderr,
                flush=True,
            )
            traceback.print_stack()
            return _original_interrupt_main(*args, **kwargs)

        _thread_mod.interrupt_main = _debug_interrupt_main  # type: ignore[method-assign]
    except Exception as exc:
        print(f"[daemon] DEBUG: failed to patch interrupt_main: {exc}", file=sys.stderr)

    _original_raise_signal = signal.raise_signal

    def _debug_raise_signal(signum: signal.Signals) -> None:
        print(
            f"\n[daemon] DEBUG: signal.raise_signal({signum!r}) called",
            file=sys.stderr,
            flush=True,
        )
        traceback.print_stack()
        return _original_raise_signal(signum)

    signal.raise_signal = _debug_raise_signal  # type: ignore[method-assign, assignment]

    _original_kill = os.kill

    def _debug_kill(pid: int, sig: int, /) -> None:
        if sig not in (0,):
            print(
                f"\n[daemon] DEBUG: os.kill(pid={pid}, sig={sig}) called",
                file=sys.stderr,
                flush=True,
            )
            traceback.print_stack()
        return _original_kill(pid, sig)

    os.kill = _debug_kill  # type: ignore[method-assign, assignment]


_WIN_DEFAULT_SIGINT_IGNORE = 15.0


def _ignore_startup_keyboard_interrupt(
    startup_time: float,
    shield_seconds: float,
) -> bool:
    if shield_seconds <= 0:
        return False
    age = time.monotonic() - startup_time
    if age >= shield_seconds:
        return False
    print(
        f"[daemon] WARN: ignoring spurious KeyboardInterrupt ({age:.2f}s < {shield_seconds:.1f}s)",
        file=sys.stderr,
        flush=True,
    )
    return True


def _start_webhook_background(
    host: str,
    port: int,
    *,
    debug: bool = False,
    restart_delay: float = 3.0,
    stop_event: threading.Event | None = None,
) -> None:
    """Start webhook HTTP server without threading.Thread.start() (hangs on Py3.14/Windows)."""

    def _run() -> None:
        from automation.runners.emit import emit_or_print

        while stop_event is None or not stop_event.is_set():
            try:
                if debug:
                    print("[daemon] webhook thread: importing server", flush=True)
                from automation.linear.webhook_server import serve

                if debug:
                    print("[daemon] webhook thread: serving", flush=True)
                serve(host=host, port=port)
                if stop_event is not None and stop_event.is_set():
                    break
                summary = "webhook server exited"
                detail = None
            except BaseException as exc:
                if stop_event is not None and stop_event.is_set():
                    break
                summary = str(exc)
                detail = traceback.format_exc()

            from automation.runners.runtime_state import get_runtime_state

            try:
                get_runtime_state().webhook_status = "crashed"
            except RuntimeError:
                pass
            emit_or_print(
                "daemon",
                "webhook.crashed",
                summary,
                detail=detail,
                plain_prefix=f"[daemon] webhook crashed: {summary}",
            )
            if restart_delay > 0:
                emit_or_print(
                    "daemon",
                    "webhook.restarting",
                    f"restart in {restart_delay:g}s",
                    plain_prefix=f"[daemon] restarting webhook in {restart_delay:g}s",
                )
                if stop_event is not None:
                    if stop_event.wait(timeout=restart_delay):
                        break
                else:
                    time.sleep(restart_delay)
            else:
                time.sleep(0)

    import _thread

    if debug:
        print("[daemon] before _thread.start_new_thread", flush=True)
    tid = _thread.start_new_thread(_run, ())
    if debug:
        print(f"[daemon] after _thread.start_new_thread tid={tid}", flush=True)


def _worker_loop(
    cfg: dict[str, Any],
    poll: float,
    webhook_enabled: bool,
    host: str,
    port: int,
    path: str,
    stop_event: threading.Event,
    display_mode: str,
    bus: EventBus,
) -> None:
    from automation.runners.emit import emit_or_print
    from automation.runners.job_worker import run_once

    _ = bus  # emit uses module-global bus from init_emit
    _ = path
    idle_ticks = 0
    while not stop_event.is_set():
        try:
            had_job = run_once(cfg, quiet_idle=True)
        except KeyboardInterrupt:
            stop_event.set()
            raise
        except Exception as exc:
            emit_or_print(
                "daemon",
                "worker.error",
                str(exc),
                plain_prefix=f"[daemon] worker error: {exc}",
            )
            had_job = False

        if had_job:
            idle_ticks = 0
        else:
            idle_ticks += 1
            if display_mode == "plain" and (idle_ticks == 1 or idle_ticks % 20 == 0):
                stats: dict[str, int] = {}
                try:
                    from automation.runners.job_worker import _queue

                    stats = _queue(cfg).stats()
                except Exception:
                    pass
                suffix = ""
                if webhook_enabled:
                    suffix = f" webhook=http://{host}:{port}/health"
                idle_msg = (
                    f"[daemon] idle (queued={stats.get('queued', '?')} "
                    f"running={stats.get('running', '?')}){suffix}"
                )
                emit_or_print(
                    "daemon",
                    "worker.idle",
                    idle_msg.removeprefix("[daemon] "),
                    plain_prefix=idle_msg,
                )

        if stop_event.wait(timeout=poll):
            break


def main(argv: list[str] | None = None) -> int:
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root))

    parser = argparse.ArgumentParser(
        description="NovelGuard automation daemon (Linear webhook + worker loop)",
    )
    parser.add_argument(
        "--no-webhook",
        action="store_true",
        help="Worker loop only (webhook serve disabled)",
    )
    parser.add_argument(
        "--poll",
        type=float,
        default=0.0,
        help="Poll interval seconds (default: config daemon.poll_seconds or 15)",
    )
    parser.add_argument(
        "--debug-interrupts",
        action="store_true",
        help="Log signal / interrupt_main / raise_signal / os.kill sources",
    )
    parser.add_argument(
        "--ignore-startup-sigint",
        type=float,
        default=None,
        metavar="SECONDS",
        help=(
            "Ignore SIGINT for first N seconds (default: 15 on Windows, 0 elsewhere). "
            "Use 0 with --strict-signals to disable."
        ),
    )
    parser.add_argument(
        "--strict-signals",
        action="store_true",
        help="Do not ignore spurious startup SIGINT (Windows/Cursor workaround off)",
    )
    parser.add_argument(
        "--plain",
        action="store_true",
        help="Line logs only; no Rich dashboard",
    )
    parser.add_argument(
        "--tui",
        action="store_true",
        help="Force Rich dashboard",
    )
    args = parser.parse_args(argv)

    from automation.runners.display_mode import resolve_display_mode

    ci = bool(os.environ.get("CI"))
    display_mode = resolve_display_mode(args, stdout_isatty=sys.stdout.isatty(), ci=ci)

    if args.strict_signals:
        sigint_ignore = 0.0
    elif args.ignore_startup_sigint is not None:
        sigint_ignore = max(0.0, float(args.ignore_startup_sigint))
    elif sys.platform == "win32":
        sigint_ignore = _WIN_DEFAULT_SIGINT_IGNORE
    else:
        sigint_ignore = 0.0

    _install_signal_handlers(startup_ignore_seconds=sigint_ignore, debug=args.debug_interrupts)
    if args.debug_interrupts:
        print("[daemon] DEBUG: interrupt tracing enabled", flush=True)
    if sigint_ignore > 0:
        print(
            f"[daemon] SIGINT shield: ignoring spurious Ctrl+C for first {sigint_ignore:.0f}s",
            flush=True,
        )

    from automation.runners.config import load_config
    from automation.runners.job_worker import run_once
    from automation.runners.worker_lock import (
        acquire_daemon_lock,
        release_daemon_lock,
        release_stale_locks,
        resolve_locks_dir,
    )

    os.environ["NOVELGUARD_AUTOMATION_DAEMON"] = "1"
    if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except (OSError, ValueError):
            pass
    script_path = Path(__file__).resolve()
    print(f"[daemon] script={script_path}", flush=True)
    print("[daemon] starting...", flush=True)

    if sys.platform == "win32" and sys.version_info >= (3, 14):
        print(
            "[daemon] WARN: Python 3.14 on Windows can be flaky for automation; "
            "recreate venv with: py -3.12 -m venv .venv",
            flush=True,
        )

    startup_time = time.monotonic()
    while True:
        try:
            cfg = load_config()
            break
        except KeyboardInterrupt:
            if not _ignore_startup_keyboard_interrupt(startup_time, sigint_ignore):
                print("\n[daemon] stopped (interrupt)", flush=True)
                return 130

    if display_mode == "tui":
        try:
            from automation.runners.tui_dashboard import ensure_rich_available

            ensure_rich_available()
        except RuntimeError as exc:
            print(str(exc), file=sys.stderr)
            return 2
    daemon_cfg = cfg.get("daemon") or {}
    linear = cfg.get("linear") or {}
    poll = args.poll or float(daemon_cfg.get("poll_seconds") or 15)
    webhook = not args.no_webhook and bool(daemon_cfg.get("webhook", True))
    host = str(linear.get("webhook_host") or "127.0.0.1")
    port = int(linear.get("webhook_port") or 8765)
    path = str(linear.get("webhook_path") or "/linear/webhook")

    locks_dir = resolve_locks_dir(cfg)
    webhook_enabled = False
    webhook_stop_event = threading.Event()

    try:
        acquire_daemon_lock(locks_dir)
    except RuntimeError as exc:
        print(f"[daemon] {exc}", file=sys.stderr)
        return 1

    from automation.runners.emit import emit_or_print, init_emit
    from automation.runners.event_bus import EventBus
    from automation.runners.runtime_state import get_runtime_state, init_runtime_state

    bus = EventBus()
    init_runtime_state(
        webhook_enabled=webhook,
        host=host,
        port=port,
        path=path,
        poll=poll,
    )
    init_emit(mode=display_mode, bus=bus)

    emit_or_print("daemon", "config.ok", "config ok", plain_prefix="[daemon] config ok")

    cleared = release_stale_locks(cfg)
    if cleared:
        emit_or_print(
            "daemon",
            "locks.cleared",
            ", ".join(cleared),
            plain_prefix=f"[daemon] cleared stale locks: {', '.join(cleared)}",
        )

    from automation.runners.job_worker import _queue

    recovered = _queue(cfg).recover_orphaned_running(locks_dir)
    if recovered:
        emit_or_print(
            "daemon",
            "queue.recovered",
            ", ".join(recovered),
            plain_prefix=f"[daemon] re-queued orphaned jobs: {', '.join(recovered)}",
        )

    emit_or_print("daemon", "lock.ok", "lock ok", plain_prefix="[daemon] lock ok")

    exit_code = 0
    try:
        if webhook:
            emit_or_print(
                "daemon",
                "webhook.starting",
                f"http://{host}:{port}{path}",
                plain_prefix=f"[daemon] starting webhook http://{host}:{port}{path}",
            )
            _start_webhook_background(
                host,
                port,
                debug=args.debug_interrupts,
                stop_event=webhook_stop_event,
            )
            webhook_enabled = True
            get_runtime_state().webhook_status = "running"
            emit_or_print(
                "daemon",
                "webhook.running",
                "webhook running",
                plain_prefix="[daemon] webhook running",
            )

            emit_or_print(
                "daemon",
                "webhook.ngrok",
                f"ngrok http {port}",
                plain_prefix=f"[daemon] ngrok: keep existing tunnel or run: ngrok http {port}",
            )
            public = str(linear.get("webhook_public_url") or "").rstrip("/")
            if public:
                emit_or_print(
                    "daemon",
                    "webhook.url",
                    f"{public}{path}",
                    plain_prefix=f"[daemon] Linear webhook URL: {public}{path}",
                )
            else:
                emit_or_print(
                    "daemon",
                    "webhook.url",
                    f"https://<ngrok-host>{path}",
                    plain_prefix=f"[daemon] Linear webhook URL: https://<ngrok-host>{path}",
                )

        emit_or_print(
            "daemon",
            "worker.poll",
            f"poll every {poll}s",
            plain_prefix=f"[daemon] worker poll every {poll}s (Ctrl+C to stop)",
        )

        while True:
            stop_event: threading.Event | None = None
            worker_thread: threading.Thread | None = None
            try:
                if display_mode == "plain":
                    idle_ticks = 0
                    while True:
                        try:
                            had_job = run_once(cfg, quiet_idle=True)
                        except KeyboardInterrupt:
                            raise
                        except Exception as exc:
                            emit_or_print(
                                "daemon",
                                "worker.error",
                                str(exc),
                                plain_prefix=f"[daemon] worker error: {exc}",
                            )
                            had_job = False

                        if had_job:
                            idle_ticks = 0
                        else:
                            idle_ticks += 1
                            if idle_ticks == 1 or idle_ticks % 20 == 0:
                                stats: dict[str, int] = {}
                                try:
                                    from automation.runners.job_worker import _queue

                                    stats = _queue(cfg).stats()
                                except Exception:
                                    pass
                                suffix = ""
                                if webhook_enabled:
                                    suffix = f" webhook=http://{host}:{port}/health"
                                idle_msg = (
                                    f"[daemon] idle (queued={stats.get('queued', '?')} "
                                    f"running={stats.get('running', '?')}){suffix}"
                                )
                                emit_or_print(
                                    "daemon",
                                    "worker.idle",
                                    idle_msg.removeprefix("[daemon] "),
                                    plain_prefix=idle_msg,
                                )
                        time.sleep(poll)
                else:
                    from automation.runners.tui_dashboard import run_live

                    stop_event = threading.Event()
                    from automation.runners.worker_context import set_stop_event

                    set_stop_event(stop_event)

                    def refresh_stats() -> None:
                        state = get_runtime_state()
                        try:
                            from automation.runners.job_worker import _queue

                            stats = _queue(cfg).stats()
                            state.queued = stats.get("queued")
                            state.running = stats.get("running")
                            state.succeeded = stats.get("succeeded")
                            state.failed = stats.get("failed")
                        except Exception:
                            pass
                        if state.cursor_running or state.verify_running:
                            from automation.runners.cursor_runner import get_cursor_pid
                            from automation.runners.git_snapshot import read_git_status_short

                            state.cursor_pid = get_cursor_pid()
                            count, lines = read_git_status_short(
                                state.active_repo_path, max_lines=10
                            )
                            state.git_changed_count = count
                            state.git_status_lines = tuple(lines)
                        else:
                            state.cursor_pid = None
                            state.git_changed_count = None
                            state.git_status_lines = ()

                    worker_thread = threading.Thread(
                        target=_worker_loop,
                        args=(
                            cfg,
                            poll,
                            webhook_enabled,
                            host,
                            port,
                            path,
                            stop_event,
                            display_mode,
                            bus,
                        ),
                        daemon=False,
                    )
                    worker_thread.start()
                    try:
                        run_live(
                            stop_event=stop_event,
                            worker_thread=worker_thread,
                            state=get_runtime_state(),
                            bus=bus,
                            refresh_stats=refresh_stats,
                        )
                    except KeyboardInterrupt:
                        stop_event.set()
                        if worker_thread.is_alive():
                            worker_thread.join(timeout=5.0)
                        raise
                break
            except KeyboardInterrupt:
                if stop_event is not None:
                    stop_event.set()
                if worker_thread is not None and worker_thread.is_alive():
                    worker_thread.join(timeout=5.0)
                if _ignore_startup_keyboard_interrupt(startup_time, sigint_ignore):
                    continue
                raise
    except KeyboardInterrupt:
        print("\n[daemon] stopped (interrupt)", flush=True)
        if args.debug_interrupts:
            print("[daemon] DEBUG: KeyboardInterrupt traceback:", file=sys.stderr, flush=True)
            traceback.print_exc()
        exit_code = 130
    except BaseException as exc:
        print(f"\n[daemon] fatal: {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
        traceback.print_exc()
        exit_code = 1
    finally:
        from automation.runners.worker_context import set_stop_event

        webhook_stop_event.set()
        set_stop_event(None)
        release_daemon_lock(locks_dir)

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
