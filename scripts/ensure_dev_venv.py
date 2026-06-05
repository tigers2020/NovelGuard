"""Ensure repo .venv uses Python 3.12 and is ready for desktop (gui) dev."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENV_DIR = ROOT / ".venv"
VENV_PY = VENV_DIR / "Scripts" / "python.exe"
MIN_VERSION = (3, 12)
MAX_VERSION = (3, 13)  # 3.12.x only

_HOST_CANDIDATES: list[list[str]] = [
    ["py", "-V:Astral/CPython3.12.13"],
    ["py", "-3.12"],
    ["py", "-3.12-64"],
]


def _version_tuple(exe: Path) -> tuple[int, int, int]:
    proc = subprocess.run(
        [str(exe), "-c", "import sys; print(*sys.version_info[:3])"],
        check=True,
        capture_output=True,
        text=True,
    )
    major, minor, patch = (int(part) for part in proc.stdout.strip().split())
    return major, minor, patch


def _version_ok(version: tuple[int, int, int]) -> bool:
    major, minor, _patch = version
    return (major, minor) >= MIN_VERSION and (major, minor) < MAX_VERSION


def _find_host_python() -> Path:
    errors: list[str] = []
    for cmd in _HOST_CANDIDATES:
        try:
            proc = subprocess.run(
                [*cmd, "-c", "import sys; print(sys.executable)"],
                check=True,
                capture_output=True,
                text=True,
            )
        except (FileNotFoundError, subprocess.CalledProcessError) as exc:
            errors.append(f"{' '.join(cmd)}: {exc}")
            continue
        exe = Path(proc.stdout.strip())
        if not exe.is_file():
            errors.append(f"{' '.join(cmd)}: missing executable {exe}")
            continue
        version = _version_tuple(exe)
        if _version_ok(version):
            return exe
        errors.append(f"{exe}: Python {version[0]}.{version[1]} (need 3.12.x)")

    tried = "\n  ".join(errors) if errors else "(no launcher candidates)"
    raise SystemExit(
        "Python 3.12 not found.\n"
        "Install Python 3.12 (python.org or `uv python install 3.12`) and retry.\n"
        f"Tried:\n  {tried}"
    )


def _remove_venv() -> None:
    if VENV_DIR.exists():
        shutil.rmtree(VENV_DIR)


def _create_venv(host: Path) -> None:
    print(f"+ {host} -m venv {VENV_DIR}")
    subprocess.run([str(host), "-m", "venv", str(VENV_DIR)], check=True)


def _install_gui(py: Path) -> None:
    subprocess.run([str(py), "-m", "pip", "install", "--upgrade", "pip"], check=True)
    subprocess.run(
        [str(py), "-m", "pip", "install", "--no-user", "-e", ".[gui]"],
        cwd=ROOT,
        check=True,
    )


def ensure_venv(*, recreate_if_wrong: bool, install_gui: bool) -> int:
    if VENV_PY.is_file():
        version = _version_tuple(VENV_PY)
        if not _version_ok(version):
            if not recreate_if_wrong:
                print(
                    f".venv is Python {version[0]}.{version[1]}.{version[2]}; need 3.12.x.\n"
                    "Delete .venv and re-run, or pass --recreate-if-wrong.",
                    file=sys.stderr,
                )
                return 1
            print(f"Recreating .venv (was Python {version[0]}.{version[1]}.{version[2]}).")
            _remove_venv()

    if not VENV_PY.is_file():
        host = _find_host_python()
        _create_venv(host)

    version = _version_tuple(VENV_PY)
    print(f"[ok] .venv Python {version[0]}.{version[1]}.{version[2]} -> {VENV_PY}")

    if install_gui:
        print("Installing editable package with gui extras into .venv ...")
        _install_gui(VENV_PY)

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--recreate-if-wrong",
        action="store_true",
        help="Delete and recreate .venv when it is not Python 3.12.x",
    )
    parser.add_argument(
        "--install-gui",
        action="store_true",
        help="pip install -e '.[gui]' into .venv after ensure",
    )
    args = parser.parse_args()
    return ensure_venv(recreate_if_wrong=args.recreate_if_wrong, install_gui=args.install_gui)


if __name__ == "__main__":
    raise SystemExit(main())
