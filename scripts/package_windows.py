"""Windows onedir package: frontend build, build stamp, PyInstaller, verify (PR-24 Task 7)."""

from __future__ import annotations

import datetime as dt
import importlib.util
import json
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
WEB_DIR = ROOT / "web"
WEB_BUILD = WEB_DIR / "build"
PYINSTALLER_BUILD = ROOT / "build"
PACKAGE_DIR = ROOT / "dist" / "NovelGuard"
EXE_PATH = PACKAGE_DIR / "NovelGuard.exe"
SPEC_PATH = ROOT / "packaging" / "NovelGuard.spec"
MANIFEST_PATH = PACKAGE_DIR / "build-manifest.json"
STAMP_FILE = SRC / "app" / "_build_stamp.py"

sys.path.insert(0, str(SRC))


def run(cmd: list[str], *, cwd: Path | None = None) -> None:
    print("+", " ".join(cmd))
    subprocess.run(cmd, cwd=str(cwd or ROOT), check=True)


def require_module(module_name: str, install_hint: str) -> None:
    if importlib.util.find_spec(module_name) is None:
        raise SystemExit(
            f"Missing required module: {module_name}\nInstall hint: {install_hint}"
        )


def require_npm() -> str:
    npm = shutil.which("npm")
    if npm is None:
        raise SystemExit(
            "Missing required command: npm\n"
            "Install Node.js and ensure npm is on PATH."
        )
    return npm


def _remove_tree(path: Path) -> None:
    def onexc(func, item: str, exc: BaseException) -> None:
        if not isinstance(exc, PermissionError):
            raise exc
        os.chmod(item, stat.S_IWUSR)
        func(item)

    shutil.rmtree(path, onexc=onexc)


def _remove_path(path: Path) -> None:
    if not path.exists():
        return
    print(f"Removing {path}")
    if path.is_file():
        path.unlink()
        return
    try:
        _remove_tree(path)
    except OSError as exc:
        if path != PACKAGE_DIR:
            raise
        stamp = dt.datetime.now(dt.UTC).strftime("%Y%m%dT%H%M%SZ")
        backup = path.with_name(f"{path.name}.bak.{stamp}")
        print(f"WARN: could not delete {path} ({exc}); renaming to {backup.name}")
        path.rename(backup)


def clean() -> None:
    for path in [WEB_BUILD, PYINSTALLER_BUILD, PACKAGE_DIR, STAMP_FILE]:
        _remove_path(path)


def frontend_build(npm: str) -> None:
    if not (WEB_DIR / "node_modules").exists():
        if (WEB_DIR / "package-lock.json").is_file():
            run([npm, "ci"], cwd=WEB_DIR)
        else:
            run([npm, "install"], cwd=WEB_DIR)

    run([npm, "run", "build"], cwd=WEB_DIR)

    index = WEB_BUILD / "index.html"
    if not index.is_file():
        raise SystemExit(f"Frontend build missing: {index}")


def git_commit() -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(ROOT),
            check=True,
            text=True,
            capture_output=True,
        )
        return result.stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def pyinstaller_build() -> None:
    run(
        [
            sys.executable,
            "-m",
            "PyInstaller",
            str(SPEC_PATH),
            "--noconfirm",
            "--clean",
        ],
        cwd=ROOT,
    )


def verify_package() -> list[str]:
    errors: list[str] = []

    if not EXE_PATH.is_file():
        errors.append(f"Missing exe: {EXE_PATH}")

    bundled_indexes = list(PACKAGE_DIR.rglob("web/build/index.html"))
    if not bundled_indexes:
        errors.append("Missing bundled web/build/index.html")

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        raise SystemExit(1)

    return [str(path.relative_to(PACKAGE_DIR)) for path in bundled_indexes]


def write_manifest(bundled_indexes: list[str], *, built_at: str, commit: str | None) -> None:
    manifest = {
        "appName": "NovelGuard",
        "buildType": "packaged",
        "gitCommit": commit,
        "builtAt": built_at,
        "pythonExecutable": sys.executable,
        "pythonVersion": sys.version,
        "packageDir": str(PACKAGE_DIR),
        "exePath": str(EXE_PATH),
        "frontendBuild": "web/build",
        "bundledIndexes": bundled_indexes,
    }
    MANIFEST_PATH.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    print(f"Python: {sys.executable}")
    print(f"Version: {sys.version}")

    require_module("PyInstaller", "pip install pyinstaller")
    require_module("webview", 'pip install -e ".[gui]"')
    npm = require_npm()

    clean()
    frontend_build(npm)

    built_at = dt.datetime.now(dt.UTC).isoformat()
    commit = git_commit()

    from app.version import apply_build_stamp

    apply_build_stamp(
        build_type="packaged",
        git_commit=commit,
        built_at=built_at,
    )

    if not STAMP_FILE.is_file():
        raise SystemExit(f"Build stamp file not written: {STAMP_FILE}")

    pyinstaller_build()
    bundled_indexes = verify_package()
    write_manifest(bundled_indexes, built_at=built_at, commit=commit)

    print(f"Package ready: {EXE_PATH}")
    print(f"Manifest: {MANIFEST_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
