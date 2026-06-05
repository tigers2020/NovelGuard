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
import time
import traceback
from pathlib import Path
from types import FrameType


def _locks_dir(cfg: dict) -> Path:
    from automation.runners.config import repo_root

    locks_dir = Path(cfg.get("locks", {}).get("dir", "automation/locks"))
    if not locks_dir.is_absolute():
        locks_dir = repo_root() / locks_dir
    return locks_dir


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


def _start_webhook_background(host: str, port: int, *, debug: bool = False) -> None:
    """Start webhook HTTP server without threading.Thread.start() (hangs on Py3.14/Windows)."""

    def _run() -> None:
        try:
            if debug:
                print("[daemon] webhook thread: importing server", flush=True)
            from automation.linear.webhook_server import serve

            if debug:
                print("[daemon] webhook thread: serving", flush=True)
            serve(host=host, port=port)
        except BaseException:
            print("[daemon] FATAL: webhook background crashed", file=sys.stderr, flush=True)
            traceback.print_exc()
            raise

    import _thread

    if debug:
        print("[daemon] before _thread.start_new_thread", flush=True)
    tid = _thread.start_new_thread(_run, ())
    if debug:
        print(f"[daemon] after _thread.start_new_thread tid={tid}", flush=True)


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
    args = parser.parse_args(argv)

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
    )

    os.environ["NOVELGUARD_AUTOMATION_DAEMON"] = "1"
    script_path = Path(__file__).resolve()
    print(f"[daemon] script={script_path}", flush=True)
    print("[daemon] starting...", flush=True)

    if sys.version_info >= (3, 14):
        print(
            "[daemon] WARN: Python 3.14 on Windows can be flaky for automation; "
            "recreate venv with: py -3.12 -m venv .venv",
            flush=True,
        )

    cfg = load_config()
    print("[daemon] config ok", flush=True)
    daemon_cfg = cfg.get("daemon") or {}
    linear = cfg.get("linear") or {}
    poll = args.poll or float(daemon_cfg.get("poll_seconds") or 15)
    webhook = not args.no_webhook and bool(daemon_cfg.get("webhook", True))
    host = str(linear.get("webhook_host") or "127.0.0.1")
    port = int(linear.get("webhook_port") or 8765)
    path = str(linear.get("webhook_path") or "/linear/webhook")

    locks_dir = _locks_dir(cfg)
    webhook_enabled = False

    try:
        acquire_daemon_lock(locks_dir)
    except RuntimeError as exc:
        print(f"[daemon] {exc}", file=sys.stderr)
        return 1

    cleared = release_stale_locks(cfg)
    if cleared:
        print(f"[daemon] cleared stale locks: {', '.join(cleared)}")

    print("[daemon] lock ok", flush=True)

    exit_code = 0
    try:
        if webhook:
            print(
                f"[daemon] starting webhook http://{host}:{port}{path}",
                flush=True,
            )
            _start_webhook_background(host, port, debug=args.debug_interrupts)
            webhook_enabled = True
            print("[daemon] webhook running", flush=True)

            print(
                f"[daemon] ngrok: keep existing tunnel or run: ngrok http {port}",
                flush=True,
            )
            public = str(linear.get("webhook_public_url") or "").rstrip("/")
            if public:
                print(f"[daemon] Linear webhook URL: {public}{path}", flush=True)
            else:
                print(
                    f"[daemon] Linear webhook URL: https://<ngrok-host>{path}",
                    flush=True,
                )

        print(f"[daemon] worker poll every {poll}s (Ctrl+C to stop)", flush=True)

        idle_ticks = 0
        while True:
            try:
                had_job = run_once(cfg, quiet_idle=True)
            except KeyboardInterrupt:
                raise
            except Exception as exc:
                print(f"[daemon] worker error: {exc}", file=sys.stderr)
                had_job = False

            if had_job:
                idle_ticks = 0
            else:
                idle_ticks += 1
                if idle_ticks == 1 or idle_ticks % 20 == 0:
                    stats = {}
                    try:
                        from automation.runners.job_worker import _queue

                        stats = _queue(cfg).stats()
                    except Exception:
                        pass
                    suffix = ""
                    if webhook_enabled:
                        suffix = f" webhook=http://{host}:{port}/health"
                    print(
                        f"[daemon] idle (queued={stats.get('queued', '?')} "
                        f"running={stats.get('running', '?')}){suffix}",
                        flush=True,
                    )
                time.sleep(poll)
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
        release_daemon_lock(locks_dir)

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
