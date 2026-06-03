"""Static packaging readiness checks for PR-24 (CI-safe; no PyInstaller run)."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

_SCRIPTS = ROOT / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from smoke_packaged_ui import (  # noqa: E402
    check_frontend_build_markers,
    check_packaged_bundle_markers,
    check_source_markers,
)

RUNTIME_CRITICAL = [
    ROOT / "src" / "app" / "webview_main.py",
    ROOT / "src" / "app" / "runtime_paths.py",
    ROOT / "src" / "app" / "version.py",
    ROOT / "scripts" / "package_windows.py",
    ROOT / "packaging" / "NovelGuard.spec",
    ROOT / "run.bat",
]


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def require_exists(path: Path, errors: list[str]) -> None:
    if not path.exists():
        errors.append(f"missing: {rel(path)}")


def require_contains(path: Path, needle: str, errors: list[str]) -> None:
    if not path.exists():
        errors.append(f"missing: {rel(path)}")
        return
    text = read(path)
    if needle not in text:
        errors.append(f"{rel(path)} does not contain {needle!r}")


def check_vite_outdir(errors: list[str]) -> None:
    path = ROOT / "web" / "vite.config.ts"
    require_exists(path, errors)
    if not path.exists():
        return
    text = read(path)
    if not re.search(r"outDir\s*:\s*[\"']build[\"']", text):
        errors.append("web/vite.config.ts must set build.outDir to 'build'")


def check_no_web_dist_in_runtime(errors: list[str]) -> None:
    for path in RUNTIME_CRITICAL:
        if not path.exists():
            continue
        text = read(path)
        if "web/dist" in text:
            errors.append(f"{rel(path)} must not reference web/dist (use web/build)")


def check_runtime_uses_web_build(errors: list[str]) -> None:
    runtime_paths = ROOT / "src" / "app" / "runtime_paths.py"
    require_exists(runtime_paths, errors)
    if not runtime_paths.exists():
        return
    text = read(runtime_paths)
    if '"web" / "build"' not in text and "'web' / 'build'" not in text:
        errors.append(f"{rel(runtime_paths)} must resolve frozen assets to web/build")


def check_package_artifacts(warnings: list[str], errors: list[str]) -> None:
    package_dir = ROOT / "dist" / "NovelGuard"
    if not package_dir.exists():
        warnings.append("optional package artifact check skipped: dist/NovelGuard not found")
        return

    exe = package_dir / "NovelGuard.exe"
    manifest = package_dir / "build-manifest.json"
    if not exe.is_file():
        errors.append("package exists but NovelGuard.exe missing")
    if not manifest.is_file():
        errors.append("package exists but build-manifest.json missing")

    indexes = list(package_dir.rglob("web/build/index.html"))
    if not indexes:
        errors.append("package exists but bundled web/build/index.html missing")


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []

    required_files = [
        "docs/superpowers/specs/012-2026-06-02-packaging-distribution-design.md",
        "docs/superpowers/plans/018-2026-06-02-pr24-packaging-distribution.md",
        "packaging/NovelGuard.spec",
        "scripts/package_windows.py",
        "src/app/runtime_paths.py",
        "src/app/version.py",
        "web/vite.config.ts",
    ]
    for item in required_files:
        require_exists(ROOT / item, errors)

    check_vite_outdir(errors)
    check_no_web_dist_in_runtime(errors)
    check_runtime_uses_web_build(errors)

    spec = ROOT / "packaging" / "NovelGuard.spec"
    require_contains(spec, "web/build", errors)
    require_contains(spec, "webview_main.py", errors)
    require_contains(spec, "NovelGuard", errors)

    package_script = ROOT / "scripts" / "package_windows.py"
    require_contains(package_script, "npm", errors)
    require_contains(package_script, "PyInstaller", errors)
    require_contains(package_script, "build-manifest.json", errors)
    require_contains(package_script, "web/build/index.html", errors)

    bridge_errors = ROOT / "web" / "src" / "bridge" / "bridgeErrors.ts"
    bridge_factory = ROOT / "web" / "src" / "bridge" / "bridgeFactory.ts"
    require_contains(bridge_errors, "PRODUCTION_BRIDGE_UNAVAILABLE", errors)
    require_contains(bridge_errors, "DEV_BRIDGE_UNAVAILABLE", errors)
    require_contains(bridge_factory, "VITE_USE_MOCK_BRIDGE", errors)
    require_contains(bridge_factory, "BRIDGE_ERROR_CODES", errors)

    version_py = ROOT / "src" / "app" / "version.py"
    require_contains(version_py, "get_app_info", errors)
    require_contains(version_py, "apply_build_stamp", errors)

    check_package_artifacts(warnings, errors)
    check_source_markers(errors)
    check_frontend_build_markers(warnings, errors)
    check_packaged_bundle_markers(warnings, errors)

    for warning in warnings:
        print(f"WARNING: {warning}")

    if errors:
        print("Packaging verification failed:")
        for error in errors:
            print(f"  - {error}")
        return 1

    print("Packaging verification passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
