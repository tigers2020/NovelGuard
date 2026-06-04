"""Post–UI-overhaul packaging smoke helpers (PR-44).

CI-safe: validates that shipped UI markers exist in source and, when present,
in a built `web/build` tree or `dist/NovelGuard` bundle. Does not launch exe.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Stable `data-testid` anchors from PR-33..43 (platform release gate).
UI_SMOKE_MARKERS: tuple[str, ...] = (
    "scan-section",
    "work-mode-tab-",  # WorkModeTabs: work-mode-tab-${tab.id}
    "resolve-workspace",
    "finalize-subflow-dialog",
    "shell-file-dock",
    "app-header",
    "app-sidebar",
    "global-command-bar",
    "settings-route",
    "logs-route",
)


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _collect_files(tree: Path, globs: tuple[str, ...]) -> list[Path]:
    seen: set[Path] = set()
    for pattern in globs:
        for path in tree.rglob(pattern):
            if path.is_file():
                seen.add(path)
    return sorted(seen)


def check_markers_in_tree(
    tree: Path,
    patterns: tuple[str, ...],
    *,
    globs: tuple[str, ...],
    label: str,
    errors: list[str],
) -> None:
    if not tree.is_dir():
        errors.append(f"{label}: missing directory {rel(tree)}")
        return
    files = _collect_files(tree, globs)
    if not files:
        errors.append(f"{label}: no files matching {globs!r} under {rel(tree)}")
        return
    corpus = ""
    for path in files:
        try:
            corpus += path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            errors.append(f"{label}: cannot read {rel(path)} ({exc})")
            return
    missing = [marker for marker in patterns if marker not in corpus]
    if missing:
        errors.append(f"{label}: missing UI markers: {', '.join(missing)}")


def check_source_markers(errors: list[str]) -> None:
    web_src = ROOT / "web" / "src"
    check_markers_in_tree(
        web_src,
        UI_SMOKE_MARKERS,
        globs=("*.tsx", "*.ts"),
        label="web/src",
        errors=errors,
    )


def check_frontend_build_markers(
    warnings: list[str],
    errors: list[str],
    *,
    strict: bool = False,
) -> None:
    build_dir = ROOT / "web" / "build"
    if not (build_dir / "index.html").is_file():
        warnings.append("optional web/build UI marker check skipped: web/build/index.html missing")
        return
    bucket = errors if strict else warnings
    check_markers_in_tree(
        build_dir,
        UI_SMOKE_MARKERS,
        globs=("*.js",),
        label="web/build",
        errors=bucket,
    )


def check_packaged_bundle_markers(
    warnings: list[str],
    errors: list[str],
    *,
    strict: bool = False,
) -> None:
    package_dir = ROOT / "dist" / "NovelGuard"
    if not package_dir.is_dir():
        warnings.append("optional dist UI marker check skipped: dist/NovelGuard not found")
        return
    bucket = errors if strict else warnings
    indexes = list(package_dir.rglob("web/build/index.html"))
    if not indexes:
        bucket.append("dist/NovelGuard exists but web/build/index.html not found in bundle")
        return
    roots = {index.parent for index in indexes}
    for build_root in roots:
        check_markers_in_tree(
            build_root,
            UI_SMOKE_MARKERS,
            globs=("*.js",),
            label=f"package ({rel(build_root)})",
            errors=bucket,
        )


def run_checks(*, require_build: bool = False) -> int:
    errors: list[str] = []
    warnings: list[str] = []

    check_source_markers(errors)
    strict = require_build
    check_frontend_build_markers(warnings, errors, strict=strict)
    check_packaged_bundle_markers(warnings, errors, strict=strict)

    for warning in warnings:
        print(f"WARNING: {warning}")

    if errors:
        print("Packaged UI smoke checks failed:")
        for error in errors:
            print(f"  - {error}")
        return 1

    print("Packaged UI smoke checks passed.")
    return 0


def main() -> int:
    require_build = "--require-build" in sys.argv
    return run_checks(require_build=require_build)


if __name__ == "__main__":
    raise SystemExit(main())
